from flask import Blueprint, jsonify, request, current_app, send_file
from flask_login import current_user, login_required
from project.utils.sql_models import Distribution, Organization, Submission
import os
from project.utils.docx import generate_docx_report
from project.utils.report_parser import process_all_reports

# Create the blueprint
data_bp = Blueprint('data', __name__)
website_name = os.environ.get("WEBSITE_NAME", "default_website_name")

@data_bp.route("/api/distribution_fetch", methods=["GET", "POST"], strict_slashes=False)
@login_required
def distribution_manager():
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
#@login_required
def proxy_fasta1():
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta')
    
@data_bp.route("/api/proxy_fai_EPI_ISL_412866")
#@login_required
def proxy_fai1():
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta.fai')

@data_bp.route("/api/proxy_gzi_EPI_ISL_412866")
#@login_required
def proxy_gzi1():
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.fasta.gz')

@data_bp.route("/api/proxy_gff3_EPI_ISL_412866")
#@login_required
def proxy_gff1():
    return current_app.send_static_file('genomes/EPI_ISL_412866/EPI_ISL_412866.gff3')

@data_bp.route("/api/proxy_fasta_EPI_ISL_1653999")
#@login_required
def proxy_fasta2():
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta')
    
@data_bp.route("/api/proxy_fai_EPI_ISL_1653999")
#@login_required
def proxy_fai2():
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta.fai')

@data_bp.route("/api/proxy_gzi_EPI_ISL_1653999")
#@login_required
def proxy_gzi2():
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta.gz')

@data_bp.route("/api/proxy_gff3_EPI_ISL_1653999")
#@login_required
def proxy_gff2():
    return current_app.send_static_file('genomes/EPI_ISL_1653999/EPI_ISL_1653999.gff3')

# Route to serve static bam
@data_bp.route("/api/distribution_data/<distribution>/sample/<selected_sample>/participant/<participant>", methods=["GET"])
#@login_required
def get_sample_bam(distribution,selected_sample,participant):
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
                bam_url = f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{lab}"
                bigwig_url = f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{lab}.bw"
                bams.append(bam_url)
                bigwigs.append(bigwig_url)

        # Compute aggregated metrics by sequencing type (exclude user lab and reference lab "9999")
        seq_aggregates = {}
        for lab, metrics in sample_details[selected_sample]["metrics"].items():
            # Exclude the logged-in user's lab and reference lab from this aggregation
            if lab == current_user.organization or lab == "9999":
                continue
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
                agg["read_coverage"] = round(agg["read_coverage"] / agg["count"], 2)
                agg["clade"] = max(agg["clade_counts"], key=agg["clade_counts"].get) if agg["clade_counts"] else ""
                agg["G_clade"] = max(agg["g_clade_counts"], key=agg["g_clade_counts"].get) if agg["g_clade_counts"] else ""
            else:
                agg["coverage"] = agg["Ns"] = agg["similarity"] = agg["read_coverage"] = 0
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
                user_bam_url = [f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{user_lab}"]
                user_bigwig_url = [f"http://{website_name}/api/distribution_data/{distribution}/sample/{selected_sample}/participant/{user_lab}.bw"]

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
    """Route for generating the DOCX report."""
    dist = Distribution.query.filter_by(name=distribution).first()
    base_dir = f"data/{dist.name}"  # Root directory for lab reports
    report_data = process_all_reports(base_dir)

    # Generate the DOCX file using the refactored function
    doc = generate_docx_report(report_data, base_dir, current_user.role, current_user.organization, distribution)

    # Save the DOCX file to a temporary file
    file_path = "/usr/src/app/project/temp_report.docx"
    doc.save(file_path)

    # Send the file to the user
    return send_file(file_path, as_attachment=True)

