from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from project.utils.sql_models import db, User, Distribution, Organization, Submission
import os, redis, gzip, pysam, shutil, subprocess
from datetime import datetime
from werkzeug.utils import secure_filename
from rq import Queue, Connection

# Create the blueprint
upload_bp = Blueprint('upload', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")

# Upload route
@upload_bp.route("/api/upload", methods=["POST"])
@login_required  # Ensure the user is authenticated
def upload_files():
    #######################this needs a lot of validation logic, and tasks sendings
    def is_gzip_file(file_path):
        """Check if a file is gzip-compressed."""
        try:
            with gzip.open(file_path, 'rb') as test_gzip:
                test_gzip.read(1)
            return True
        except gzip.BadGzipFile:
            return False
        
    def read_first_lines(file_path, num_lines=4):
        """Read first lines of a file, handling gzip if necessary."""
        open_func = gzip.open if is_gzip_file(file_path) else open
        with open_func(file_path, 'rt') as f:  # Read as text
            return [f.readline().strip() for _ in range(num_lines)]
        
    def is_valid_fasta(file_path):
        """Check if the file is a valid FASTA."""
        try:
            first_line = read_first_lines(file_path, 1)[0]
            return first_line.startswith(">")
        except Exception:
            return False

    def is_valid_bam(file_path):
        """Check if the file is a valid BAM using pysam."""
        try:
            with pysam.AlignmentFile(file_path, "rb") as _:
                return True
        except Exception:
            return False

    def is_valid_fastq(file_path):
        """Check if the file follows the FASTQ format."""
        try:
            lines = read_first_lines(file_path, 4)
            return (lines[0].startswith("@") and
                    all(c in "ATCGN" for c in lines[1]) and
                    lines[2] == "+" and
                    len(lines[1]) == len(lines[3]))
        except Exception:
            return False
    
    # Validate request form data
    required_fields = ['sample', 'distribution', 'organization','sequencing_type']
    for field in required_fields:
        if field not in request.form:
            return jsonify({"error": f"{field} is required"}), 400
    
    # Get form data
    sequencing_type = request.form['sequencing_type']
    fasta_file = request.files.get('fasta')
    bam_file = request.files.get('bam')
    fq1 = request.files.get('fq1')
    fq2 = request.files.get('fq2')
    description = request.form.get('description', '')  # Optional description
    sample = request.form['sample']
    distribution = request.form['distribution']
    organization = request.form['organization']
    
    # Ensure at least one file is provided
    if not any([fasta_file, bam_file, fq1, fq2]):
        return jsonify({"error": "At least one file (fasta, bam or fastq) is required"}), 400

    # Create upload folder
    specific_upload_folder = os.path.join(
        current_app.config["UPLOAD_FOLDER"], distribution, organization, sample
    )

    samples_txt=os.path.join(
        current_app.config["UPLOAD_FOLDER"], distribution,"samples.txt")

    # Check if the folder exists, and delete it if it does
    if os.path.exists(specific_upload_folder):
        shutil.rmtree(specific_upload_folder)

    # Now recreate the folder
    os.makedirs(specific_upload_folder, exist_ok=True)

        # Save files with validation
    uploaded_files = {}
    if fasta_file:
        fasta_filename = secure_filename(organization+"_"+sample + "_original.fasta")
        fasta_path = os.path.join(specific_upload_folder, fasta_filename)
        fasta_file.seek(0)
        fasta_file.save(fasta_path)

        if not is_valid_fasta(fasta_path):
            os.remove(fasta_path)
            return jsonify({"error": "Invalid FASTA file"}), 400
        
        uploaded_files['fasta'] = fasta_path

    if bam_file:
        bam_filename = secure_filename(organization+"_"+sample + "_original.bam")
        bam_path = os.path.join(specific_upload_folder, bam_filename)
        bam_file.seek(0)
        bam_file.save(bam_path)

        if not is_valid_bam(bam_path):
            os.remove(bam_path)
            return jsonify({"error": "Invalid BAM file"}), 400
        
        uploaded_files['bam'] = bam_path


    if fq1:
        fq1_is_gzipped = is_gzip_file(fq1)
        fq1_extension = "_original_R1.fastq.gz" if fq1_is_gzipped else "_original_R1.fastq"
        fq1_filename = secure_filename(organization + "_" + sample  + fq1_extension)
        fq1_path = os.path.join(specific_upload_folder, fq1_filename)
        fq1.seek(0)
        fq1.save(fq1_path)

        if not is_valid_fastq(fq1_path):
            os.remove(fq1_path)
            return jsonify({"error": "Invalid FASTQ R1 file"}), 400

        uploaded_files['fq1'] = fq1_path

    if fq2:
        fq2_is_gzipped = is_gzip_file(fq2)
        fq2_extension = "_original_R2.fastq.gz" if fq2_is_gzipped else "_original_R2.fastq"
        fq2_filename = secure_filename(organization + "_" + sample  + fq2_extension)
        fq2_path = os.path.join(specific_upload_folder, fq2_filename)
        fq2.seek(0)
        fq2.save(fq2_path)

        if not is_valid_fastq(fq2_path):
            os.remove(fq2_path)
            return jsonify({"error": "Invalid FASTQ R2 file"}), 400
        
        uploaded_files['fq2'] = fq2_path

    # Copy genomeLength.txt to the specific_upload_folder
    genome_length_file = os.path.join(current_app.config["UPLOAD_FOLDER"], "genomeLength.txt")
    genome_length_dest = os.path.join(specific_upload_folder, "genomeLength.txt")
    if os.path.exists(genome_length_file):
        shutil.copy(genome_length_file, genome_length_dest)
        uploaded_files['genomeLength'] = genome_length_dest
    else:
        return jsonify({"error": "genomeLength.txt not found in the upload folder"}), 400

    # Enqueue task to process files and launch workflow asynchronously
    with Connection(redis.from_url(current_app.config["REDIS_URL"])):
        q = Queue()
        task = q.enqueue(launch_nextflow, specific_upload_folder, "main.nf", {"reads": specific_upload_folder+"", "samples_txt": samples_txt})

    redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url)
    r.publish("chat",f"[UPLOAD]{organization}'s upload of sample {sample} from distribution {distribution} has been completed.")

    # Create and commit a new Submission record
    # Assuming Organization and Distribution are identified by their unique 'name'
    org_obj = Organization.query.filter_by(name=organization).first()
    dist_obj = Distribution.query.filter_by(name=distribution).first()
    user_obj = User.query.filter_by(email=current_user.id).first()
    if not org_obj or not dist_obj:
        return jsonify({"error": "Organization or distribution not found"}), 400

    submission = Submission(
        user_id=user_obj.id,
        organization_id=org_obj.id,
        distribution_id=dist_obj.id,
        sample=sample,
        sequencing_type=sequencing_type
    )
    db.session.add(submission)
    db.session.commit()

    # Return response with task information
    return jsonify({
        "message": "Files uploaded successfully, task queued.",
        "uploaded_files": uploaded_files,
        "task_id": task.get_id(),
    }), 201

# Task function for launching Nextflow
def launch_nextflow(upload_dir, workflow_name="main.nf", params={}):
    """Run the Nextflow workflow."""
    try:
        # Construct the command with escaped spaces
        cmd = " ".join([
            "nextflow", "run", workflow_name, "--reads=" + params['reads'].replace(' ', '\\ ') + "/","--samples_txt=" + params['samples_txt'].replace(' ', '\\ '), "-resume"
        ])

        print(cmd)
        
        # Log the command being executed
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] Command: {cmd}")
        
        # Execute the workflow
        process = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        # Log stdout and stderr
        stdout_timestamp = datetime.now().isoformat()
        print(f"[{stdout_timestamp}] STDOUT:\n{process.stdout}")
        
        stderr_timestamp = datetime.now().isoformat()
        if process.stderr:
            print(f"[{stderr_timestamp}] STDERR:\n{process.stderr}")

        distribution, organization, sample=upload_dir.split("/")[-3],upload_dir.split("/")[-2],upload_dir.split("/")[-1]
        redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.publish("chat", f"[ANALYSIS COMPLETE]{organization}'s analysis of sample {sample} from distribution {distribution} has been completed.")
        
        # Return the result
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "stdout": process.stdout,
            "stderr": process.stderr
        }
    except Exception as e:
        error_timestamp = datetime.now().isoformat()
        print(f"[{error_timestamp}] Exception: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

