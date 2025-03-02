"""
data.py
=======

This module provides endpoints for managing distribution data and sample reports.

It includes endpoints to:
    Fetch distributions associated with the current user's organization.
    Retrieve sample details and aggregated metrics for a distribution.
    Proxy static genome files (FASTA, FAI, GZI, GFF3) for specified references.
    Serve consensus BAM, BAI, and BigWig files for individual samples.
    Generate and download DOCX reports based on lab reports.

WARNING: the static files are consumed by JBrowse2, which cant send credentials hence the 
endpoints are available to everyone and pose a safety risk. Must be revamped.

:author: Kevin
:version: 0.0.1
:date: 2025-02-21
"""
from flask import Blueprint, jsonify, request, current_app, send_file
from flask_login import current_user, login_required
from project.utils.sql_models import Distribution, Organization, Submission
import os, zipfile, subprocess
from project.utils.docx import generate_docx_report
from project.utils.report_parser import process_all_reports
from datetime import datetime

# Create the blueprint
data_bp = Blueprint('data', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")
subdirectory_name = os.environ.get("SUBDIRECTORY_NAME", "default_subdirectory_name")

@data_bp.route("/api/distribution_fetch", methods=["GET", "POST"], strict_slashes=False)
@login_required
def distribution_manager():
    """
    Fetch distributions associated with the current user's organization.

    For GET requests, returns a JSON object with a list of distribution names
    for which the user's organization is registered.

    :return: JSON object with key "distributions" and a list of distribution names.
    :rtype: flask.Response
    """
    if request.method == "GET":
        # Fetch all distributions from the database
        distributions = Distribution.query.filter(Distribution.organizations.any(name=current_user.organization)).all()
        print(distributions)
        return jsonify({
            "distributions": [d.name for d in distributions]
        }), 200

@data_bp.route("/api/distributions/<distribution>/samples", methods=["GET", "POST"], strict_slashes=False)
@login_required
def samples_per_distro_manager(distribution):
    """
    Retrieve sample information for a specified distribution.

    For GET requests, returns a JSON object containing the distribution name
    and the list of samples registered to it.

    :param distribution: The name of the distribution.
    :type distribution: str
    :return: JSON response with distribution and sample data.
    :rtype: flask.Response
    """
    if request.method == "GET":
        # Fetch the distribution from the database
        distribution_record = Distribution.query.filter_by(name=distribution).first()

        if not distribution_record:
            return jsonify({"error": f"Distribution '{distribution}' not found"}), 404

        # Return the list of samples
        samples = distribution_record.samples or []
        print(samples)
        return jsonify({"distribution": distribution, "samples": samples}), 200
    
@data_bp.route("/api/distribution_data/<distribution>", methods=["GET"])
@login_required
def get_distribution_data(distribution):
    """
    Process and return aggregated report data for a given distribution.

    Loads a sample-to-reference mapping from 'samples.txt', processes lab reports,
    aggregates metrics for each sample, and returns the distribution data as JSON.

    :param distribution: The name of the distribution.
    :type distribution: str
    :return: JSON object containing aggregated metrics per sample.
    :rtype: flask.Response
    """
    print("Sample data request received")  # Debugging line
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    import subprocess
    subprocess.call("ls data", shell=True)
    
    # Load sample-reference mapping from samples.txt
    samples_file = f"{base_dir}/samples.txt"
    sample_reference_map = {}
    try:
        with open(samples_file, "r") as f:
            for line in f:
                sample_id, reference = line.strip().split()
                sample_reference_map[sample_id] = reference
    except FileNotFoundError:
        print(f"File not found: {samples_file}")
        return jsonify({"error": "Samples file not found"}), 404
    except Exception as e:
        print(f"Error reading samples.txt: {e}")
        return jsonify({"error": "Failed to process samples file"}), 500

    # Process reports and aggregate distribution data
    report_data = process_all_reports(base_dir)
    distribution_data = {}  # {sample_name: {"participants": int, "metrics": dict, "reference": str}}
    for lab, samples in report_data.items():
        for sample_name, metrics in samples.items():
            if sample_name not in distribution_data:
                distribution_data[sample_name] = {
                    "participants": 0,
                    "reference": sample_reference_map.get(sample_name, "Unknown")  # Add reference info
                }
            distribution_data[sample_name]["participants"] += 1

    return jsonify(distribution_data)

@data_bp.route("/api/proxy_fasta_EPI_ISL_412866")
#@login_required these endpoints are to serve files to JBrowse2, which cant send credentials.
def proxy_fasta1():
    """
    Serve the FASTA file for reference EPI_ISL_412866.

    :return: FASTA file from the static genomes directory.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta')
    
@data_bp.route("/api/proxy_fai_EPI_ISL_412866")
#@login_required
def proxy_fai1():
    """
    Serve the FAI index file for reference EPI_ISL_412866.

    :return: FAI file from the static genomes directory.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta.fai')

@data_bp.route("/api/proxy_gzi_EPI_ISL_412866")
#@login_required
def proxy_gzi1():
    """
    Serve the gzipped FASTA file for reference EPI_ISL_412866.

    :return: Gzipped FASTA file.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta.gz')

@data_bp.route("/api/proxy_gff3_EPI_ISL_412866")
#@login_required
def proxy_gff1():
    """
    Serve the GFF3 file for reference EPI_ISL_412866.

    :return: GFF3 file.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.gff3')

@data_bp.route("/api/proxy_fasta_EPI_ISL_1653999")
#@login_required
def proxy_fasta2():
    """
    Serve the FASTA file for reference EPI_ISL_1653999.

    :return: FASTA file.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta')
    
@data_bp.route("/api/proxy_fai_EPI_ISL_1653999")
#@login_required
def proxy_fai2():
    """
    Serve the FAI index file for reference EPI_ISL_1653999.

    :return: FAI file.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta.fai')

@data_bp.route("/api/proxy_gzi_EPI_ISL_1653999")
#@login_required
def proxy_gzi2():
    """
    Serve the gzipped FASTA file for reference EPI_ISL_1653999.

    :return: Gzipped FASTA file.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta.gz')

@data_bp.route("/api/proxy_gff3_EPI_ISL_1653999")
#@login_required
def proxy_gff2():
    """
    Serve the GFF3 file for reference EPI_ISL_1653999.

    :return: GFF3 file.
    :rtype: flask.Response
    """
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.gff3')

# Route to serve static bam
@data_bp.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>", methods=["GET"])
#@login_required
def get_sample_bam(distribution,selected_sample,participant):
    """
    Serve the consensus BAM file for a given sample and participant within a distribution.

    :param distribution: Name of the distribution.
    :type distribution: str
    :param selected_sample: Name of the sample.
    :type selected_sample: str
    :param participant: Participant's identifier (typically the lab name).
    :type participant: str
    :return: The consensus BAM file as an attachment.
    :rtype: flask.Response
    """
    print(f"Request received for bams")  # Debugging line
    # Define the directory where your files are stored
    dist = Distribution.query.filter_by(name=distribution).first()
    file_path = f"/usr/src/app/data/{dist.name}/{participant}/{selected_sample}/{participant}_{selected_sample}_consensus.bam"  # Replace with your directory
    print(file_path)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Serve the file
    try:
        return send_file(file_path, as_attachment=True, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to serve static bais ################################ BEWARE NO VALIDATION TO DOWNLOAD BAM FILES FOR JBROWSE, SO ANYONE CAN ACCESS, just add user and password and validate here
@data_bp.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>.bai", methods=["GET"])
#@login_required
def get_sample_bai(distribution,selected_sample,participant):
    """
    Serve the BAI index file for a consensus BAM file.

    :param distribution: Name of the distribution.
    :type distribution: str
    :param selected_sample: Name of the sample.
    :type selected_sample: str
    :param participant: Participant's identifier (typically the lab name).
    :type participant: str
    :return: The BAI file as an attachment.
    :rtype: flask.Response
    """
    print(f"Request received for bais")  # Debugging line
    # Define the directory where your files are stored
    dist = Distribution.query.filter_by(name=distribution).first()
    file_path = f"/usr/src/app/data/{dist.name}/{participant}/{selected_sample}/{participant}_{selected_sample}_consensus.bam.bai"  # Replace with your directory
    print(file_path)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Serve the file
    try:
        return send_file(file_path, as_attachment=True, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to serve static bigwig
@data_bp.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>.bw", methods=["GET"])
#@login_required
def get_sample_bigwig(distribution,selected_sample,participant):
    """
    Serve the BigWig file for a given sample and participant.

    :param distribution: Name of the distribution.
    :type distribution: str
    :param selected_sample: Name of the sample.
    :type selected_sample: str
    :param participant: Participant's identifier (typically the lab name).
    :type participant: str
    :return: The BigWig file as an attachment.
    :rtype: flask.Response
    """
    print(f"Request received for bams")  # Debugging line
    # Define the directory where your files are stored
    dist = Distribution.query.filter_by(name=distribution).first()
    file_path = f"/usr/src/app/data/{dist.name}/{participant}/{selected_sample}/{participant}_{selected_sample}.bw"  # Replace with your directory
    print(file_path)

    # Check if the file exists
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    # Serve the file
    try:
        return send_file(file_path, as_attachment=True, mimetype='application/octet-stream')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_bp.route("/api/distribution_data/<distribution>/sample/<selected_sample>", methods=["GET"])
@login_required
def get_sample_details(distribution, selected_sample):
    """
    Retrieve detailed report data and aggregated metrics for a specific sample within a distribution.

    Processes lab reports from the distribution's data folder, aggregates metrics across participants,
    and returns both individual and aggregated data. For superusers, all data is returned;
    otherwise, only data relevant to the user's organization is provided.

    :param distribution: Name of the distribution.
    :type distribution: str
    :param selected_sample: Name of the sample.
    :type selected_sample: str
    :return: A JSON object with table data, file URLs (BAM/BigWig), and aggregated sequencing metrics.
    :rtype: flask.Response
    """
    print(f"Request received for sample: {selected_sample}")  # Debugging line
    print(distribution)
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    print(base_dir)
    report_data = process_all_reports(base_dir)

    sample_details = {}  # {sample_name: {"participants": int, "metrics": dict}}
    for lab, samples in report_data.items():
        for sample_name, metrics in samples.items():
            if sample_name not in sample_details:
                sample_details[sample_name] = {
                    "participants": 0,
                    "metrics": {},
                }
            sample_details[sample_name]["metrics"][lab] = metrics
            sample_details[sample_name]["participants"] += 1

    # Handle form submission
    if selected_sample in sample_details:
        # Prepare table data and FASTA URLs
        table_data = []
        bams = []
        bigwigs = []
        for lab, metrics in sample_details[selected_sample]["metrics"].items():
            submission = (
                Submission.query
                .join(Organization)
                .filter(
                    Submission.distribution_id == dist.id,
                    Submission.sample == selected_sample,
                    Organization.name == lab
                )
                .first()
            )
            if submission:
                seq_type = submission.sequencing_type
            else:
                seq_type = "N/A"
                
            if metrics["coverage"] == "N/A":
                table_data.append({
                "participant": lab,
                "coverage": 'N/A',
                "ns": 'N/A',
                "similarity": 'N/A',
                "read_coverage": 'N/A',
                "clade":'N/A',
                "G_clade":'N/A',
                "sequencing_type": seq_type
                })
                continue  # Skip this lab if coverage is not a number

            read_coverage=round(metrics["Mean coverage depth"], 2) if metrics["Mean coverage depth"]!="N/A" else "N/A"
            table_data.append({
                "participant": lab,
                "coverage": round(metrics["coverage"] * 100, 2),
                "ns": round(metrics["Ns"], 2),
                "similarity": round(metrics["similarity"], 2),
                "read_coverage": read_coverage,
                "clade":metrics["clade"],
                "G_clade":metrics["G_clade"],
                "sequencing_type": seq_type
            })
            if read_coverage!="N/A":
                bam_url = f"http://{website_name}{subdirectory_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{lab}"
                bigwig_url = f"http://{website_name}{subdirectory_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{lab}.bw"
                bams.append(bam_url)
                bigwigs.append(bigwig_url)

        # Compute aggregated metrics by sequencing type (exclude user lab and reference lab "9999")
        seq_aggregates = {}
        for lab, metrics in sample_details[selected_sample]["metrics"].items():
            # Exclude the logged-in user's lab and reference lab from this aggregation
            # if lab == current_user.organization or lab == "9999":
            #    continue
            submission = (
                Submission.query
                .join(Organization)
                .filter(
                    Submission.distribution_id == dist.id,
                    Submission.sample == selected_sample,
                    Organization.name == lab
                )
                .first()
            )
            if submission:
                lab_seq_type = submission.sequencing_type
            else:
                lab_seq_type = "N/A"
            if lab_seq_type not in seq_aggregates:
                seq_aggregates[lab_seq_type] = {
                    "coverage": 0,
                    "Ns": 0,
                    "similarity": 0,
                    "read_coverage": 0,
                    "count": 0,
                    "read_count": 0,
                    "clade_counts": {},
                    "g_clade_counts": {}
                }
            if metrics["coverage"] == "N/A":
                continue
            group = seq_aggregates[lab_seq_type]
            group["coverage"] += metrics["coverage"]
            group["Ns"] += metrics["Ns"]
            group["similarity"] += metrics["similarity"]
            if metrics["Mean coverage depth"] != "N/A":
                group["read_coverage"] += metrics["Mean coverage depth"]
                group["read_count"] += 1
            group["count"] += 1
            clade = metrics.get("clade", "")
            g_clade = metrics.get("G_clade", "")
            if clade:
                group["clade_counts"][clade] = group["clade_counts"].get(clade, 0) + 1
            if g_clade:
                group["g_clade_counts"][g_clade] = group["g_clade_counts"].get(g_clade, 0) + 1

        # Finalize aggregated metrics per sequencing type
        for seq_type, agg in seq_aggregates.items():
            if agg["count"] > 0:
                agg["coverage"] = round((agg["coverage"] / agg["count"]) * 100, 2)
                agg["Ns"] = round(agg["Ns"] / agg["count"], 2)
                agg["similarity"] = round(agg["similarity"] / agg["count"], 2)
                
                agg["clade"] = max(agg["clade_counts"], key=agg["clade_counts"].get) if agg["clade_counts"] else ""
                agg["G_clade"] = max(agg["g_clade_counts"], key=agg["g_clade_counts"].get) if agg["g_clade_counts"] else ""
                if agg["read_count"]!=0:
                    agg["read_coverage"] = round(agg["read_coverage"] / agg["read_count"], 2)
                else:
                    agg["read_coverage"] = ""
            else:
                agg["coverage"] = agg["Ns"] = agg["similarity"] = agg["read_coverage"] = ""
                agg["clade"] = agg["G_clade"] = ""
              
        if current_user.is_superuser():
            return jsonify({"table": table_data, "bams": bams, "bigwigs": bigwigs, "sequencing_aggregates": seq_aggregates})
        else:
            print('non superuser')
            user_lab = current_user.organization
            if user_lab not in sample_details[selected_sample]["metrics"]:
                return jsonify({"error": "You have not submitted valid data for this sample."}), 404

            # Query the submission for the logged-in user's lab
            user_submission = (
                Submission.query
                .join(Organization)
                .filter(
                    Submission.distribution_id == dist.id,
                    Submission.sample == selected_sample,
                    Organization.name == user_lab
                )
                .first()
            )
            if user_submission:
                user_seq_type = user_submission.sequencing_type
            else:
                user_seq_type = "N/A"

            # Filter user lab data
            user_metrics = sample_details[selected_sample]["metrics"][user_lab]
            if user_metrics["coverage"]=="N/A":
                return jsonify({"error": "You have not submitted valid data for this sample."}), 404
            print(user_metrics)
            user_bam_url=[]
            user_bigwig_url=[]
            plot_url=""
            if "Mean coverage depth" in user_metrics and user_metrics["Mean coverage depth"]!="N/A":
                user_bam_url = [f"http://{website_name}{subdirectory_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{user_lab}"]
                user_bigwig_url = [f"http://{website_name}{subdirectory_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{user_lab}.bw"]

            # Aggregate metrics from other labs
            aggregated_metrics = {
                "coverage": 0,
                "ns": 0,
                "similarity": 0,
                "read_coverage": 0,
                "lab_count": 0,
                "clade":"",
                "G_clade":""
            }

            clade_counts = {}
            g_clade_counts = {}

            for lab, metrics in sample_details[selected_sample]["metrics"].items():
                if lab != user_lab and lab != "9999":  # Aggregate metrics from other labs
                    if metrics["coverage"] == "N/A":
                        continue  # Skip this lab if coverage is not a number
                    aggregated_metrics["coverage"] += metrics["coverage"]
                    aggregated_metrics["ns"] += metrics["Ns"]
                    aggregated_metrics["similarity"] += metrics["similarity"]
                    if metrics["Mean coverage depth"]!="N/A":
                        aggregated_metrics["read_coverage"] += metrics["Mean coverage depth"]
                    aggregated_metrics["lab_count"] += 1

                    # Count clade occurrences
                    clade = metrics.get("clade", "")
                    g_clade = metrics.get("G_clade", "")
                    if clade:
                        clade_counts[clade] = clade_counts.get(clade, 0) + 1
                    if g_clade:
                        g_clade_counts[g_clade] = g_clade_counts.get(g_clade, 0) + 1

            # Calculate averages for aggregated metrics
            if aggregated_metrics["lab_count"] > 0:
                aggregated_metrics["coverage"] = round(
                    (aggregated_metrics["coverage"] / aggregated_metrics["lab_count"]) * 100, 2
                )
                aggregated_metrics["ns"] = round(
                    aggregated_metrics["ns"] / aggregated_metrics["lab_count"], 2
                )
                aggregated_metrics["similarity"] = round(
                    aggregated_metrics["similarity"] / aggregated_metrics["lab_count"], 2
                )
                aggregated_metrics["read_coverage"] = round(
                    aggregated_metrics["read_coverage"] / aggregated_metrics["lab_count"], 2
                )

            # Determine the most frequent clade and G_clade
            if clade_counts:
                aggregated_metrics["clade"] = max(clade_counts, key=clade_counts.get)
            if g_clade_counts:
                aggregated_metrics["G_clade"] = max(g_clade_counts, key=g_clade_counts.get)

            # Extract reference lab metrics (Lab 9999)
            ref_lab = "9999"
            ref_metrics = sample_details[selected_sample]["metrics"].get(ref_lab, None)
            if not ref_metrics:
                return jsonify({"error": "Reference lab data not found"}), 404
            # Query the submission for the logged-in user's lab
            ref_submission = (
                Submission.query
                .join(Organization)
                .filter(
                    Submission.distribution_id == dist.id,
                    Submission.sample == selected_sample,
                    Organization.name == ref_lab
                )
                .first()
            )
            if ref_submission:
                ref_seq_type = ref_submission.sequencing_type
            else:
                ref_seq_type = "N/A"

            # Prepare response table data
            others_label="Others ("+str(aggregated_metrics["lab_count"])+")"
            user_table_data = [
                {
                    "participant": user_lab,
                    "coverage": round(user_metrics["coverage"] * 100, 2),
                    "ns": round(user_metrics["Ns"], 2),
                    "similarity": round(user_metrics["similarity"], 2),
                    "read_coverage": round(user_metrics["Mean coverage depth"], 2) if user_metrics["Mean coverage depth"]!="N/A" else "N/A",
                    "clade":user_metrics["clade"],
                    "G_clade":user_metrics["G_clade"],
                    "sequencing_type": user_seq_type
                },
                {
                    "participant": others_label,
                    "coverage": aggregated_metrics["coverage"],
                    "ns": aggregated_metrics["ns"],
                    "similarity": aggregated_metrics["similarity"],
                    "read_coverage": aggregated_metrics["read_coverage"],
                    "clade":aggregated_metrics["clade"],
                    "G_clade":aggregated_metrics["G_clade"],
                    "sequencing_type": ""
                },
                {
                    "participant": "Reference",
                    "coverage": round(ref_metrics["coverage"] * 100, 2),
                    "ns": round(ref_metrics["Ns"], 2),
                    "similarity": round(ref_metrics["similarity"], 2),
                    "read_coverage": round(ref_metrics["Mean coverage depth"], 2) if ref_metrics["Mean coverage depth"]!="N/A" else "N/A",
                    "clade":ref_metrics["clade"],
                    "G_clade":ref_metrics["G_clade"],
                    "sequencing_type": ref_seq_type  # Optionally add a sequencing type for the reference row if desired
                }
            ]

            return jsonify({"table": user_table_data, "bams": user_bam_url, "bigwigs": user_bigwig_url, "sequencing_aggregates": seq_aggregates})

    return jsonify({"error": "Sample not found"}), 404

@data_bp.route("/api/download_docx/<distribution>")
@login_required
def download_docx(distribution):
    """
    Generate and send a DOCX report for a specified distribution.

    Processes lab reports from the distribution's data folder to generate a DOCX report,
    saves it temporarily, and returns the file as an attachment. Report is rendered differently,
    depending on user's privileges.

    :param distribution: The name of the distribution.
    :type distribution: str
    :return: The generated DOCX report file.
    :rtype: flask.Response
    """
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    report_data = process_all_reports(base_dir)

    # Generate the DOCX file using the refactored function
    doc = generate_docx_report(report_data, base_dir, current_user.role, current_user.organization, distribution)

    # Save the DOCX file to a temporary file
    file_path = f"/usr/src/app/project/static/reports/MIC_{current_user.organization}_WG_{distribution}_Report.docx" # save to pdf
    doc.save(file_path)

    # Send the file to the user
    return send_file(file_path, as_attachment=True)

@data_bp.route("/api/download_docx_all/<distribution>")
@login_required
def download_docx_all(distribution):
    """
    Generate and send a ZIP containing DOCX reports for all organizations in a distribution.

    TO DO: send this task to a worker instead of having the main application do all the work. And create necessary views to serve the final zip elsewhere.

    :param distribution: The name of the distribution.
    :type distribution: str
    :return: A ZIP file containing the generated DOCX reports.
    :rtype: flask.Response
    """
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    temp_dir = f"/usr/src/app/project/static/reports/all_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    os.makedirs(temp_dir, exist_ok=True)
    zip_filename = f"reports_{distribution}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    zip_path = os.path.join(temp_dir, zip_filename)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for org in dist.organizations:
            report_data = process_all_reports(base_dir)
            doc = generate_docx_report(report_data, base_dir, "user", org.name, distribution)

            # Save each DOCX report
            docx_filename = f"MIC_{org.name}_WG_{distribution}_Report.docx"
            docx_path = os.path.join(temp_dir, docx_filename)
            doc.save(docx_path)

            # Build the PDF filename and path (assumes .docx becomes .pdf)
            pdf_filename = docx_filename.replace(".docx", ".pdf")
            pdf_path = os.path.join(temp_dir, pdf_filename)

            # Convert the DOCX to PDF using LibreOffice in headless mode
            subprocess.run([
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                docx_path,
                "--outdir", temp_dir
            ], check=True)

            # Add the PDF file to the ZIP archive
            zipf.write(pdf_path, arcname=pdf_filename)

            # Clean up: remove the temporary DOCX and PDF files
            os.remove(docx_path)
            os.remove(pdf_path)

    # Send the ZIP file to the user
    return send_file(zip_path, as_attachment=True, download_name=zip_filename)