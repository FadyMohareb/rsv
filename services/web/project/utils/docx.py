"""
docx.py
=======
This utilities module is in charge of processing the data of a distribution and preparing its docx report.

Functions:

    generate_sample_plot_pdf(sample_name, sample_data, role)
        Creates a stacked bar and line graph for sample data visualization.

    create_pygenometracks_plot(reference_genome, annotation, region, bed_path, bigwig_file, bigwig_consensus_file, output_dir, sample_name, user_lab)
        Uses pyGenomeTracks to generate genome coverage plots.

    create_element(name)
        Creates an XML element for DOCX formatting.

    create_attribute(element, name, value)
        Adds an attribute to an XML element.

    add_page_number(run)
        Inserts a page number field in a DOCX document.
    
    generate_docx_reportreport_data, base_dir, role, user_lab, distribution
        Generates a DOCX report summarizing viric genome analysis results.

:author: Kevin
:version: 0.0.1
:date: 2025-02-21
"""

import datetime
from io import BytesIO
from docx import Document
from docx.shared import Inches,Pt, Cm, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_BREAK, WD_COLOR_INDEX
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, ns
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml
from project.utils.report_parser import process_all_reports
import matplotlib.pyplot as plt
import numpy as np
import os
import subprocess
import shutil

def generate_sample_plot_pdf(sample_name, sample_data, role):
    """
    Generates a stacked bar and line graph using Matplotlib for a given sample.

    :param sample_name: The name of the sample, used for file naming.
    :type sample_name: str
    :param sample_data: Dictionary containing sample statistics (coverage, similarity, etc.).
    :type sample_data: dict
    :param role: User role (affects visualisation style).
    :type role: str
    :return: The file path of the generated plot image.
    :rtype: str
    """
    
    # Extract the data for plotting (adjust based on your dataset structure)
    labs = list(sample_data.keys())
    
    # Replace 'WR006' with 'reference' and anonymize the rest of the participants
    anonymized_labs = [lab for i, lab in enumerate(labs)]  # ['reference' if lab == 'WR024' else f'{i}' for i, lab in enumerate(labs)]
    
    genome_coverage_percent = [sample_data[lab]["coverage"] * 100 if sample_data[lab]["coverage"]!="N/A" else 0 for lab in labs]  # Genome coverage at a specific threshold
    similarity_percent = [sample_data[lab]["similarity"] if sample_data[lab]["coverage"]!="N/A" else 0 for lab in labs]  # Could be uniformity or another similarity metric
    num_ns_percent = [sample_data[lab]["Ns"]if sample_data[lab]["coverage"]!="N/A" else 0 for lab in labs]  # Total number of non-ACGTNs
    read_coverage = [sample_data[lab]["Mean coverage depth"] if sample_data[lab]["Mean coverage depth"]!="N/A" else 0 for lab in labs]  # Read depth or other coverage metric

    # Create the figure and primary axis (ax1) with a wider figure size
    fig, ax1 = plt.subplots(figsize=(16, 8))  # Increased width for a wider figure
    
    """    if role == "user":
        # Horizontal Bar Plot Configuration
        y_pos = np.arange(len(labs))
        bar_height = 0.3  # Limiting bar height (make it a bit thinner)

        # Plot bars for Genome Coverage and Ns
        ax1.barh(y_pos, genome_coverage_percent, bar_height, label="Genome Coverage (%)", color="#1E3A5F", zorder=3)
        ax1.barh(y_pos, num_ns_percent, bar_height, left=genome_coverage_percent, label="Ns in Sequence (%)", color="#FBC02D", zorder=3)

        # Plot a separate bar for Similarity
        ax1.barh(y_pos + bar_height, similarity_percent, bar_height, label="Similarity (%)", color="#F57C00", zorder=3)

        ax1.set_ylabel("Participant", fontsize=18)
        ax1.set_xlabel("Percentage (%)", fontsize=18)
        ax1.set_yticks(y_pos + bar_height / 2)
        ax1.set_yticklabels(anonymized_labs, fontsize=16)
        ax1.invert_yaxis()  # Invert y-axis for better readability

        # Secondary axis for Read Coverage
        ax2 = ax1.twiny()
        ax2.plot(read_coverage, y_pos, label="Read Coverage (Mean)", color="black", marker="o", linestyle="--", linewidth=2)
        ax2.set_xlabel("Read Coverage (Mean)", fontsize=18)
        ax2.set_xlim(left=0, right=max(read_coverage) * 1.1)

    else:
    """
    # Vertical Bar Plot Configuration (Default)
    bar_width = 0.3  # Limiting bar width (make it a bit narrower)
    x_pos = np.arange(len(labs))

    # Plot bars for Genome Coverage and Ns
    ax1.bar(x_pos, genome_coverage_percent, bar_width, label="Genome Coverage (%)", color="#1E3A5F", zorder=3)
    ax1.bar(x_pos, num_ns_percent, bar_width, bottom=genome_coverage_percent, label="Ns in Sequence (%)", color="#FBC02D", zorder=3)

    # Plot a separate bar for Similarity
    ax1.bar(x_pos + bar_width, similarity_percent, bar_width, label="Similarity (%)", color="#F57C00", zorder=3)

    ax1.set_xlabel("Participant", fontsize=18)
    ax1.set_ylabel("Percentage (%)", fontsize=18)
    ax1.set_xticks(x_pos + bar_width / 2)
    ax1.set_xticklabels(anonymized_labs, rotation=45, ha="right", fontsize=16)

    # Secondary axis for Read Coverage
    ax2 = ax1.twinx()
    ax2.plot(x_pos, read_coverage, label="Read Coverage (Mean)", color="black", marker="o", linestyle="--", linewidth=2)
    ax2.set_ylabel("Read Coverage (Mean)", fontsize=18)
    ax2.set_ylim(bottom=0, top=max(read_coverage) * 1.1)

    # Add horizontal lines for thresholds
    '''if role == "user":
        ax1.axvline(90, color="grey", linestyle="--", linewidth=1, label="_nolegend_", zorder=-1)
        ax1.axvline(98, color="blue", linestyle="--", linewidth=1, zorder=-1)
    else:'''
    ax1.axhline(90, color="grey", linestyle="--", linewidth=1, label="_nolegend_", zorder=-1)
    ax1.axhline(98, color="blue", linestyle="--", linewidth=1, zorder=-1)

    # Adjust the legend placement to the right of the plot to save vertical space
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    
    '''if role == "user":
        # Combine the legends and place them to the right with a larger font size
        ax1.legend(handles=handles1 + handles2, labels=labels1 + labels2, 
                loc='upper left', bbox_to_anchor=(1, 1),fontsize=16, frameon=False)
    else:'''
    ax1.legend(handles=handles1 + handles2, labels=labels1 + labels2, 
               loc='upper center', bbox_to_anchor=(0.5, -0.27), ncol=3, fontsize=18)
        
    # Adjust the layout to prevent clipping of labels and legends
    fig.tight_layout()  # Increase padding to avoid overlapping and give extra space to the legend

    # Save the plot as a PNG image (or you can save as PDF if required)
    plt.savefig(f'{sample_name}_metrics_plot.png', dpi=300, bbox_inches='tight')  # Ensure tight bounding box

    return f'{sample_name}_metrics_plot.png'  # Path to the saved plot image


def create_pygenometracks_plot(reference_genome, annotation, region, bed_path, bigwig_file, bigwig_consensus_file, output_dir, sample_name, user_lab):
    """
    Generates a genome coverage plot using pyGenomeTracks for a specific user_lab.

    Creates a tracks.ini file that configures:
      - A reference track (FASTA),
      - An annotation track (GFF3),
      - A bigwig track (BigWig file).

    :param reference_genome: Path to the reference genome FASTA file.
    :type reference_genome: str
    :param annotation: Path to the GFF3 annotation file.
    :type annotation: str
    :param region: Genomic region to visualize.
    :type region: str
    :param bed_path: Path to the BED file with sequence variants.
    :type bed_path: str
    :param bigwig_file: Path to the BigWig file containing read coverage data.
    :type bigwig_file: str
    :param bigwig_consensus_file: Path to the consensus BigWig file.
    :type bigwig_consensus_file: str
    :param output_dir: Directory where the plot and ini file will be saved.
    :type output_dir: str
    :param sample_name: Sample identifier.
    :type sample_name: str
    :param user_lab: User lab identifier.
    :type user_lab: str
    :return: File path of the generated coverage plot.
    :rtype: str
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    tracks_ini = os.path.join(output_dir, f"{user_lab}_{sample_name}_tracks.ini")
    plot_output = os.path.join(output_dir, f"{user_lab}_{sample_name}_coverage_plot.png")

    # Create tracks.ini configuration with three sections:
    # Reference, Annotation, and BigWig
    tracks=f"""
        [annotation]
        file = {annotation}
        title = {reference_genome.split("/")[-1].split(".")[0]} genes
        prefered_name = gene_name
        color = green
        style = UCSC
        height = 2
        file_type = gtf
        merge_transcripts = true

        [bed]
        file = {bed_path}
        title = Seq. variants
        color = purple
        height = 3
        file_type = bed

        [bigwig]
        file = {bigwig_consensus_file}
        title = Seq. coverage
        color = grey
        height = 1
        file_type = bigwig
        """
    # Only write the read coverage bigwig section if reads were uploaded
    if bigwig_file!=None:
            tracks+=f"""
            
        [bigwig]
        file = {bigwig_file}
        title = Read Coverage
        color = blue
        height = 3
        file_type = bigwig
        """
    with open(tracks_ini, "w") as ini:
        ini.write(tracks)

    # Run pyGenomeTracks to generate the plot for the given region
    command = [
        "pyGenomeTracks",
        "--tracks", tracks_ini,
        "--region", region,
        "--outFileName", plot_output,
        "--dpi", str(300)
    ]
    
    try:
        subprocess.run(command, check=True)
        return plot_output  # Return the path to the generated image
    except subprocess.CalledProcessError as e:
        print(f"Error generating plot: {e}")
        return None


def create_element(name):
    """
    Creates an XML element for use in DOCX formatting.

    :param name: The name of the XML element.
    :type name: str
    :return: The created XML element.
    :rtype: OxmlElement
    """
    return OxmlElement(name)

def create_attribute(element, name, value):
    """
    Adds an attribute to an XML element.

    :param element: The XML element to modify.
    :type element: OxmlElement
    :param name: The attribute name.
    :type name: str
    :param value: The attribute value.
    :type value: str
    """
    element.set(ns.qn(name), value)

def add_page_number(run):
    """
    Inserts a page number field in a DOCX document.

    :param run: A DOCX run object where the page number field is inserted.
    :type run: docx.text.run.Run
    """
    fldChar1 = create_element('w:fldChar')
    create_attribute(fldChar1, 'w:fldCharType', 'begin')

    instrText = create_element('w:instrText')
    create_attribute(instrText, 'xml:space', 'preserve')
    instrText.text = "PAGE"

    fldChar2 = create_element('w:fldChar')
    create_attribute(fldChar2, 'w:fldCharType', 'end')

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)

def generate_docx_report(report_data, base_dir, role, user_lab, distribution):
    """
    Generates a DOCX report summarizing genomic analysis results for a given distribution.

    The report includes sample statistics, visualizations, and formatted text.

    :param report_data: Processed data containing genomic viral analysis results.
    :type report_data: dict
    :param base_dir: Base directory containing report-related files.
    :type base_dir: str
    :param role: User role determining report formatting.
    :type role: str
    :param user_lab: User lab identifier.
    :type user_lab: str
    :param distribution: The distribution to .
    :type distribution: str
    :return: the generated DOCX report.
    :rtype: docx
    """
    report_data = process_all_reports(base_dir)
    distribution=str(base_dir.split("/")[1])
    samples_file = f"{base_dir}/samples.txt"
    sample_reference_map = {}
    with open(samples_file, "r") as f:
        for line in f:
            sample_id, reference = line.strip().split()
            sample_reference_map[sample_id] = reference

    from docx.oxml import OxmlElement, ns

    def create_element(name):
        return OxmlElement(name)

    def create_attribute(element, name, value):
        element.set(ns.qn(name), value)

    def add_page_number(run):
        fldChar1 = create_element('w:fldChar')
        create_attribute(fldChar1, 'w:fldCharType', 'begin')

        instrText = create_element('w:instrText')
        create_attribute(instrText, 'xml:space', 'preserve')
        instrText.text = "PAGE"

        fldChar2 = create_element('w:fldChar')
        create_attribute(fldChar2, 'w:fldCharType', 'end')

        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)

    # Create DOCX document
    doc = Document()

    # Style
    font = doc.styles['Normal'].font
    font.name = 'Arial'
    font.size = Pt(10)
    
    #changing the page margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Cm(1)
        section.bottom_margin = Cm(1)
        section.left_margin = Cm(1)
        section.right_margin = Cm(1)

    # Add UK-NEQAS logo to the header (centered)
    header = doc.sections[0].header
    paragraph = header.paragraphs[0]
    logo_run = paragraph.add_run()
    logo_run.add_picture("project/static/uk-neqas-logo.jpg", width=Inches(2.5))
    date = doc.add_paragraph()
    date.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    text_run = date.add_run()
    text_run.text = '\t' + datetime.datetime.now().strftime("%b %d, %Y")  # For center align of text
    text_run.style = "Heading 2 Char"

    # Add a title to the document
    doc.add_heading('Quality Metrics Report', 0)

    # First page
    # Adding the lorem ipsum text to the document
    figure_count = 1
    table_count = 1
    intro = doc.add_paragraph()
    intro_run = intro.add_run("Introduction")
    intro_run.bold = True
    doc.add_paragraph(f"""Thank you for participating in the distribution {distribution} of UK NEQAS Microbiology pilot External Quality Assessment (EQA).

Samples for this EQA are distributed by UK NEQAS Microbiology and those with detectable virus are either sequenced inhouse or forwarded to the appropriate laboratory for sequencing according to routine practice.

A survey of sequencing technology is completed as part of the sequencing result upload process. FASTA, BAM and/or FASTQ files are requested to evaluate RSV sequencing quality. The sequence data submitted is also processed by the EQA to generate a lineage using Nextclade.

Your individual sequencing quality and lineage assignment report (docx format) are available on the XXXXXX website. If you have any problems accessing your reports then please contact XXXXXXXXXXXXXXXXXX (email address). 

The purpose of this EQA is to assess:
 ➢  The accuracy of RSV sequencing.
 ➢  Provide a measurement of the quality of viral sequencing.

The summary of the EQA participation, marking criteria applied, and the scoring is provided as Appendix 1.
""")
    breaks = doc.add_paragraph().add_run()
    for _ in range(4):
        breaks.add_break()

    # Add the copyright of CONFIDENTIAL label
    copyright_paragraph = doc.add_paragraph()
    copyright_run = copyright_paragraph.add_run("CONFIDENTIAL. Copyright © UKNEQAS for Microbiology")
    copyright_run.bold = True  # Bold for emphasis
    copyright_run.italic = True  # Italicize for stylistic effect
    copyright_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER  # Center the text
    copyright_run.font.size = Pt(10)  # Adjust font size for the copyright
    #copyright_run.add_break(WD_BREAK.PAGE)




    def subtype_assignment(user_subtype, intended_subtype):
        if user_subtype=="original":
            return intended_subtype
        elif user_subtype=="alternative":
            return "RSV-B" if intended_subtype=="RSV-A" else "RSV-A"
        return user_subtype  






    sample_html_reports = {}

    for lab, samples in report_data.items():
        for sample_name, metrics in samples.items():
            if sample_name not in sample_html_reports:
                sample_html_reports[sample_name] = {}
            sample_html_reports[sample_name][lab] = metrics

    def compute_evaluation_data(sample_html_reports, sample_reference_map, user_lab):
        """Computes evaluation data from sample reports."""
        
        evaluation_data = {"RSV_Subtyping": [], "Clade":[],"Legacy_clade":[], "Genome Coverage (%)": [],"Ns in Sequence (%)": [], "Similarity (%)": [],"Read Coverage (mean)": []}
        for sample_name, lab_data in sample_html_reports.items():
            lab_count = 0
            lab_pass = 0
            reference_metrics = lab_data.get("9999", {})  # Extract reference metrics
            user_metrics = lab_data.get(user_lab, {})  # Extract user metrics
            if user_metrics=={}:
                continue
            #subtype
            intended_subtype = "RSV-B" if sample_reference_map[sample_name]=="EPI_ISL_1653999" else "RSV-A"
            print(sample_name)
            print("intended_subtype ", intended_subtype)  
            reference_subtype = subtype_assignment(reference_metrics['subtype'], intended_subtype)
            print("reference_metrics['subtype'] ", reference_metrics['subtype'])
            print("reference_subtype ", reference_subtype)
            user_subtype = subtype_assignment(user_metrics['subtype'], intended_subtype)
            print("user_metrics['subtype'] ", user_metrics['subtype'])
            print("user_subtype ", user_subtype)
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999":
                    continue
                else:
                    lab_count+=1
                    if metrics["subtype"]=="original":
                        lab_pass+=1
            subtyping=[sample_name, user_subtype, intended_subtype, reference_subtype, "Pass" if user_subtype == intended_subtype else "Fail", f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["RSV_Subtyping"].append(subtyping)    
            
            #clade
            lab_count = 0
            lab_pass = 0
            intended_clade = reference_metrics["clade"]
            reference_clade = intended_clade
            user_clade = user_metrics["clade"]
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999":
                    continue
                else:
                    lab_count+=1
                    if metrics["clade"]==intended_clade:
                        lab_pass+=1
            clade=[sample_name, user_clade, intended_clade, reference_clade, "Pass" if user_clade == intended_clade else "Fail", f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["Clade"].append(clade)  

            #g_clade
            lab_count = 0
            lab_pass = 0
            intended_clade = reference_metrics["G_clade"]
            reference_clade = intended_clade
            user_clade = user_metrics["G_clade"]
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999":
                    continue
                else:
                    lab_count+=1
                    if metrics["G_clade"]==intended_clade:
                        lab_pass+=1
            g_clade=[sample_name, user_clade, intended_clade, reference_clade, "Pass" if user_clade == intended_clade else "Fail", f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["Legacy_clade"].append(g_clade)

            def format_IQR_string(aggregated_metrics):
                if not aggregated_metrics:  # Handle empty list case
                    return "N/A"

                mean_value = round(np.mean(aggregated_metrics))  # Compute mean and round
                q1, q3 = np.percentile(aggregated_metrics, [25, 75])  # Compute Q1 and Q3
                q1, q3 = round(q1), round(q3)  # Round percentiles
                
                return f"{mean_value} ({q1}-{q3})"

            #genome_coverage (these four loops could be better refactored into one)
            lab_count = 0
            lab_pass = 0
            reference_coverage = reference_metrics["coverage"]*100
            user_coverage = user_metrics["coverage"]*100
            aggregated_metrics = []
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999" or metrics["coverage"]=="N/A":
                    continue
                else:
                    lab_count+=1
                    aggregated_metrics.append(metrics["coverage"]*100)
                    if metrics["coverage"]>0.90:
                        lab_pass+=1
            coverage=[sample_name, round(user_coverage,1), "90% or higher", round(reference_coverage,1), "Pass" if user_coverage >0.90 else "Fail", format_IQR_string(aggregated_metrics), f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["Genome Coverage (%)"].append(coverage)

            #Ns
            lab_count = 0
            lab_pass = 0
            reference_n = reference_metrics["Ns"]
            user_n = user_metrics["Ns"]
            aggregated_metrics = []
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999" or metrics["coverage"]=="N/A":
                    continue
                else:
                    lab_count+=1
                    aggregated_metrics.append(metrics["Ns"])
                    if metrics["Ns"]<=2:
                        lab_pass+=1
            ns=[sample_name, round(user_n,1), "2% or lower", round(reference_n,1), "Pass" if user_n <=2 else "Fail", format_IQR_string(aggregated_metrics), f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["Ns in Sequence (%)"].append(ns)

            #similarity
            lab_count = 0
            lab_pass = 0
            reference_similarity = reference_metrics["similarity"]
            user_similarity = user_metrics["similarity"]
            aggregated_metrics = []
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999" or metrics["coverage"]=="N/A":
                    continue
                else:
                    lab_count+=1
                    aggregated_metrics.append(metrics["similarity"])
                    if metrics["similarity"]>98:
                        lab_pass+=1
            similarity=[sample_name, round(user_similarity,1), "98% or higher", round(reference_similarity,1), "Pass" if user_similarity >98 else "Fail", format_IQR_string(aggregated_metrics), f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["Similarity (%)"].append(similarity)

            #Mean coverage depth
            lab_count = 0
            lab_pass = 0
            reference_coverage = reference_metrics["Mean coverage depth"]
            user_coverage = round(user_metrics["Mean coverage depth"],0) if user_metrics["Mean coverage depth"]!="N/A" else "N/A"
            aggregated_metrics = []
            for lab, metrics in lab_data.items():
                if lab==user_lab or lab == "9999" or metrics["coverage"]=="N/A":
                    continue
                else:
                    lab_count+=1
                    if metrics["Mean coverage depth"]!="N/A":
                        aggregated_metrics.append(metrics["Mean coverage depth"])
                        if metrics["Mean coverage depth"]>50:
                            lab_pass+=1
            print(user_lab)
            print(sample_name)
            coverage=[sample_name, user_coverage, "50 or higher", round(reference_coverage,0), "Pass" if user_similarity >50 else "Fail", format_IQR_string(aggregated_metrics), f"{lab_pass}/{lab_count} ({(lab_pass * 100) // lab_count}%)"]
            evaluation_data["Read Coverage (mean)"].append(coverage)
        
        print(evaluation_data)
        return evaluation_data


    def add_evaluation_tables(doc, evaluation_data, run_id="WR024"):
        """Adds RSV Evaluation and Sequencing Quality tables to the DOCX report with transposed format."""

        def apply_color(run, text):
            """Apply color coding for pass/fail."""
            run.text = text
            if text.lower() == "pass":
                run.font.color.rgb = RGBColor(0, 128, 0)  # Green
            elif text.lower() == "fail":
                run.font.color.rgb = RGBColor(255, 0, 0)  # Red

        def apply_background_color(cell, color_rgb):
            """Apply background color to a table cell."""
            # Create the XML shading element and apply it to the cell
            cell._element.get_or_add_tcPr().append(parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_rgb)))

        def apply_font_size(cell, size_pt):
            """Apply a smaller font size to a table cell."""
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(size_pt)

        doc.add_page_break()
        doc.add_heading(f"Evaluation Report: {run_id}", level=1)

        # Table 1: RSV Subtyping and Clade Assignment
        doc.add_heading("Table 1: RSV subtyping and lineage assignment", level=2)
        table1 = doc.add_table(rows=1, cols=7)  # 7 Columns: Indicator, Specimen ID, Your result, Intended, Reference, Score, Participants
        table1.style = "Table Grid"
        table1.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Table 1 Header
        hdr_cells = table1.rows[0].cells
        headers = ["Indicator", "Specimen ID", "Your result", "Intended Result", "Reference Lab result", "Your score", "Participant with intended results"]
        for i, text in enumerate(headers):
            hdr_cells[i].text = text
            hdr_cells[i].paragraphs[0].runs[0].bold = True
            hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(10)  # Slightly smaller font size

        # Apply background color to the header row (light grey)
        for cell in hdr_cells:
            apply_background_color(cell, "D3D3D3")  # Light grey background

        # Populate Table 1 with merged Indicator cells and color rows differently
        indicator_colors = {
            "RSV_Subtyping": "FFDDC1",  # Light pink
            "Clade": "D1E8E2",  # Light teal
            "Legacy_clade": "E2D1E8",  # Light purple
        }

        for indicator in ["RSV_Subtyping", "Clade", "Legacy_clade"]:
            rows = evaluation_data[indicator]
            first_cell = None
            row_color = indicator_colors.get(indicator, "FFFFFF")  # Default to white if not found

            for i, row in enumerate(rows):
                row_cells = table1.add_row().cells
                if i == 0:
                    first_cell = row_cells[0]  # Store first cell for merging
                    if indicator=="RSV_Subtyping":
                        first_cell.text = "RSV Subtyping"
                    elif indicator=="Clade":
                        first_cell.text = "Lineage"
                    elif indicator=="Legacy_clade":
                        first_cell.text = "Legacy lineage"
                else:
                    row_cells[0]._tc.merge(first_cell._tc)  # Merge vertically

                row_cells[1].text = str(row[0])  
                row_cells[2].text = row[1] if row[1] else ""  
                row_cells[3].text = row[2] if row[2] else ""  
                row_cells[4].text = row[3] if row[3] else ""  
                apply_color(row_cells[5].paragraphs[0].add_run(), row[4])  
                row_cells[6].text = row[5]  

                # Apply background color and smaller font size to each row under the current indicator
                for cell in row_cells:
                    apply_background_color(cell, row_color)  # Apply unique color per indicator
                    apply_font_size(cell, 9)  # Set font size to 6 pt for the row

        doc.add_paragraph()  # Spacing before Table 2

        # Table 2: Sequencing Quality
        doc.add_heading("Table 2: Sequencing Quality", level=2)
        table2 = doc.add_table(rows=1, cols=8)  # 8 Columns: Indicator, Specimen ID, Your result, Recommended, Reference, Score, Mean (IQR), Participants meeting threshold
        table2.style = "Table Grid"
        table2.alignment = WD_TABLE_ALIGNMENT.CENTER

        # Create the first header row
        table2_header = table2.rows[0].cells
        headers = ["Indicator", "Specimen ID", "Your result", "Recommended Value*", "Reference Lab result", "Your score", "Participant summary"]
        for i, text in enumerate(headers):
            table2_header[i].text = text
            table2_header[i].paragraphs[0].runs[0].bold = True
            table2_header[i].paragraphs[0].runs[0].font.size = Pt(10)  # Slightly smaller font size
        table2_header[6].merge(table2_header[7])

        # Apply background color to the header row (light grey)
        for cell in table2_header:
            apply_background_color(cell, "D3D3D3")  # Light grey background

        # Add the second empty row
        empty_row = table2.add_row().cells

        # Merge all cells except the one under "Participant Summary" (column 6)
        for i in range(6):  # Merge the first 6 columns
            empty_row[i].merge(table2_header[i])

        # Split the "Participant Summary" cell into two: "Mean (IQR)" and "Participants Meeting Threshold"
        empty_row[6].text = "Mean (IQR)"
        empty_row[7].text = "Participants meeting threshold"

        # Optional: Bold the new header cells and make their font smaller
        empty_row[6].paragraphs[0].runs[0].font.size = Pt(10)  # Smaller font size
        empty_row[7].paragraphs[0].runs[0].font.size = Pt(10)  # Smaller font size

        # Apply background color to the empty row (light blue)
        for cell in empty_row:
            apply_background_color(cell, "ADD8E6")  # Light blue background

        # Populate Table 2 with merged Indicator cells and color rows differently
        indicator_colors_table2 = {
            "Genome Coverage (%)": "FFDDC1",  # Light pink
            "Ns in Sequence (%)": "D1E8E2",  # Light teal
            "Similarity (%)": "E2D1E8",  # Light purple
            "Read Coverage (mean)": "FFFACD",  # Light yellow
        }

        for indicator in ["Genome Coverage (%)", "Ns in Sequence (%)", "Similarity (%)", "Read Coverage (mean)"]:
            rows = evaluation_data[indicator]
            first_cell = None
            row_color = indicator_colors_table2.get(indicator, "FFFFFF")  # Default to white if not found

            for i, row in enumerate(rows):
                row_cells = table2.add_row().cells
                if i == 0:
                    first_cell = row_cells[0]  # Store first cell for merging
                    first_cell.text = indicator
                else:
                    row_cells[0]._tc.merge(first_cell._tc)  # Merge vertically

                row_cells[1].text = str(row[0])  
                row_cells[2].text = str(row[1])  
                row_cells[3].text = row[2]  
                row_cells[4].text = str(row[3])  
                apply_color(row_cells[5].paragraphs[0].add_run(), row[4])  
                row_cells[6].text = row[5]  
                row_cells[7].text = row[6]  

                # Apply background color and smaller font size to each row under the current indicator
                for cell in row_cells:
                    apply_background_color(cell, row_color)  # Apply unique color per indicator
                    apply_font_size(cell, 9)  # Set font size to 6 pt for the row
        
        # **Adding the Sequencing Quality Notes with Smaller Font**
        para = doc.add_paragraph("\n* Recommended Value")

        bullet_points = [
            "Obtained sufficient genome coverage (90% or higher).",
            "Maintained Ns in Sequence within acceptable limits (2% or lower).",
            "Obtained sufficient Similarity (98% or higher).",
            "Obtained sufficient Read Coverage (Mean depth of 50 or higher)."
        ]
        for point in bullet_points:
            para = doc.add_paragraph(f"{point}", style="List Bullet")
            para.runs[0].font.size = Pt(8)  # Set font size to 6 pt
        
        doc.add_page_break()


        return doc


    evaluation_data = compute_evaluation_data(sample_html_reports, sample_reference_map, user_lab)
    doc = add_evaluation_tables(doc, evaluation_data, user_lab)

    # If the user is not a superuser, filter and aggregate data
    others_label=""
    agg_users={}
    if not role == "superuser":
        processed_reports = {}
        for sample_name, labs_data in sample_html_reports.items():
            if user_lab not in labs_data:
                continue  # Skip samples the user has no access to

            user_metrics = labs_data[user_lab]
            reference_metrics = labs_data.get("9999", {})  # Extract reference metrics
            subtype_counts = {}
            clade_counts = {}
            g_clade_counts = {}

            aggregated_metrics = {
                "coverage": 0,
                "Ns": 0,
                "similarity": 0,
                "Mean coverage depth": 0,
                "lab_count": 0,
                "clade": "",
                "G_clade": "",
                "subtype":""
            }

            # Aggregate data from other labs
            for lab, metrics in labs_data.items():
                if lab != user_lab and lab != "9999" and metrics["coverage"]!="N/A":  # Exclude user lab and reference lab
                    aggregated_metrics["coverage"] += metrics["coverage"]
                    aggregated_metrics["Ns"] += metrics["Ns"]
                    aggregated_metrics["similarity"] += metrics["similarity"]
                    if metrics["Mean coverage depth"]!="N/A":
                        aggregated_metrics["Mean coverage depth"] += metrics["Mean coverage depth"]
                    aggregated_metrics["lab_count"] += 1

                    # Count clade occurrences
                    clade = metrics.get("clade", "")
                    subtype = metrics.get("subtype", "")
                    g_clade = metrics.get("G_clade", "")
                    if subtype:
                        subtype_counts[subtype] = subtype_counts.get(subtype, 0) + 1
                    if clade:
                        clade_counts[clade] = clade_counts.get(clade, 0) + 1
                    if g_clade:
                        g_clade_counts[g_clade] = g_clade_counts.get(g_clade, 0) + 1

            # Calculate averages
            if aggregated_metrics["lab_count"] > 0:
                aggregated_metrics["coverage"] = round(
                    (aggregated_metrics["coverage"] / aggregated_metrics["lab_count"]), 2
                )
                aggregated_metrics["Ns"] = round(
                    aggregated_metrics["Ns"] / aggregated_metrics["lab_count"], 2
                )
                aggregated_metrics["similarity"] = round(
                    aggregated_metrics["similarity"] / aggregated_metrics["lab_count"], 2
                )
                aggregated_metrics["Mean coverage depth"] = round(
                    aggregated_metrics["Mean coverage depth"] / aggregated_metrics["lab_count"], 2
                )

            # Determine the most frequent clades
            if subtype_counts:
                aggregated_metrics["subtype"] = max(subtype_counts, key=subtype_counts.get)
            if clade_counts:
                aggregated_metrics["clade"] = max(clade_counts, key=clade_counts.get)
            if g_clade_counts:
                aggregated_metrics["G_clade"] = max(g_clade_counts, key=g_clade_counts.get)

            # Prepare processed data for the user
            others_label="Others ("+str(aggregated_metrics["lab_count"])+")"
            processed_reports[sample_name] = {
                user_lab: user_metrics,
                others_label: aggregated_metrics,
                "Reference": reference_metrics
            }
            agg_users[sample_name]=aggregated_metrics

        sample_html_reports = processed_reports


    sample_html_reports = dict(sorted(sample_html_reports.items()))
    
    # Handle lab anonymization based on the user's role
    if role == 'superuser':
        # Iterate through each sample's data and anonymize lab names
        for sample, data in sample_html_reports.items():
            count = 1
            anonymized_data = {}
            for i, (lab, metrics) in enumerate(data.items()):
                if lab == '9999' or lab == 'Reference':
                    anonymized_data['9999'] = metrics  # Keep the reference lab as '9999'
                else:
                    anonymized_data[f'{count:01d}'] = metrics  # Anonymize labs as single-digit numbers
                    count += 1
            # Replace the sample data with anonymized data
            sample_html_reports[sample] = anonymized_data

    # Sort sample_html_reports such that '9999' comes first
    for sample, data in sample_html_reports.items():
        sorted_data = {
            key: data[key]
            for key in sorted(data, key=lambda k: (k != '9999', k))  # '9999' comes first, then rest in order
        }
        sample_html_reports[sample] = sorted_data

    # Sort the sample_html_reports dictionary by sample name
    sample_html_reports = dict(sorted(sample_html_reports.items()))



    # Add sample plots and tables to the DOCX file
    for sample, data in sample_html_reports.items():
        plot_path = generate_sample_plot_pdf(sample, data, role)  # Generate and get the plot path
        intended_subtype = "RSV-B" if sample_reference_map[sample]=="EPI_ISL_1653999" else "RSV-A"
        doc.add_heading(f'Sample {sample}', level=1)
        doc.add_heading(f'Lineage assignment', level=2)

        # Extract Clade and G_clade assignments for the 'reference'
        reference_clade = None
        reference_g_clade = None

        # Iterate through data to find the reference clade and g_clade
        for lab, metrics in data.items():
            if lab == '9999':  # Reference participant
                reference_clade = metrics['clade']
                reference_g_clade = metrics['G_clade']
                break
            elif lab== 'Reference':
                reference_subtype = subtype_assignment(metrics['subtype'], intended_subtype)
                reference_clade = metrics['clade']
                reference_g_clade = metrics['G_clade']
                break

        # Add an introductory paragraph about clade assignments
        if role=='superuser':
            #doc.add_paragraph("All participants matched RSV subtype assignments with reference lab.", style='List Bullet')
            mistakes_text = "All participants matched lineage assignments with reference lab."  # Default
            for lab, metrics in data.items():
                if lab != '9999' and lab!='Reference':  # Exclude the reference itself
                    if metrics['clade'] != reference_clade or metrics['G_clade'] != reference_g_clade:
                        mistakes_text = "Some participants' clade assignments differed from the reference lab."
                        mistakes_found = True
                        break
            doc.add_paragraph(mistakes_text, style='List Bullet')
        else:
            mistakes_text = "Your lab's lineage assignment matches the reference lab's."
            if data[user_lab]['clade'] != reference_clade:
                mistakes_text = "Your lab's lineage assignment does not match the reference lab's."
            doc.add_paragraph(mistakes_text, style='List Bullet')
        
        # Caption for the Clade table
        clade_caption = doc.add_paragraph()
        clade_caption.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        clade_runner = clade_caption.add_run(f"Table {str(table_count)}. Lineage assignments for sample {sample}, including RSV subtype.")
        clade_runner.bold = True
        clade_runner.italic = True
        table_count += 1  # Increment the table count

        # Add the Clade and G_clade table with RSV subtype
        clade_table = doc.add_table(rows=1, cols=4)  # Creating a table with 4 columns (Participant, Subtype, Clade, Legacy clade)
        clade_table.style = 'Table Grid'

        # Adding the header row for the table
        clade_hdr_cells = clade_table.rows[0].cells
        clade_hdr_cells[0].text = 'Participant'
        clade_hdr_cells[0].paragraphs[0].runs[0].bold = True
        clade_hdr_cells[1].text = 'RSV Subtype'
        clade_hdr_cells[1].paragraphs[0].runs[0].bold = True
        clade_hdr_cells[2].text = 'Lineage'
        clade_hdr_cells[2].paragraphs[0].runs[0].bold = True
        clade_hdr_cells[3].text = 'Legacy lineage'
        clade_hdr_cells[3].paragraphs[0].runs[0].bold = True

        # Adding data rows for each participant and highlighting mismatches
        labCount = 0
        for lab, metrics in data.items():
            labName=lab

            # Add a new row to the table
            row_cells = clade_table.add_row().cells

            # Participant column
            row_cells[0].text = labName
            row_cells[0].paragraphs[0].runs[0].italic = True  # Italicize the first column (Participant)

            # RSV Subtype column
            subtype_cell = row_cells[1]
            subtype_cell.text = subtype_assignment(metrics['subtype'],intended_subtype)
            # Highlight mismatched Clade values
            if metrics['subtype'] == "alternative":
                subtype_cell.paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW

            # Clade column
            clade_cell = row_cells[2]
            clade_cell.text = metrics['clade']
            # Highlight mismatched Clade values
            if metrics['clade'] != reference_clade:
                clade_cell.paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW

            # Legacy clade column
            g_clade_cell = row_cells[3]
            g_clade_cell.text = metrics['G_clade']
            # Highlight mismatched Legacy clade values
            if metrics['G_clade'] != reference_g_clade:
                g_clade_cell.paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW


        doc.add_heading(f'Sequencing quality', level=2)

                # Initialize flags to check if any participants fail to meet thresholds
        failed_coverage = []
        failed_ns = []
        failed_similarity = []
        failed_coverage_depth = []

        # Initialize user-specific flags if the role is not a superuser
        user_failed_coverage = False
        user_failed_ns = False
        user_failed_similarity = False
        user_failed_coverage_depth = False

        # Loop through the data to check conditions and generate summary statements
        for lab, metrics in data.items():
            labName = lab

            # Check thresholds for all participants if the role is superuser
            if role == "superuser":
                if metrics['coverage'] == 'N/A' or metrics['coverage'] < 0.90:
                    failed_coverage.append(labName)
                if metrics['coverage'] == 'N/A' or metrics['Ns'] > 2:
                    failed_ns.append(labName)
                if metrics['coverage'] == 'N/A' or metrics['similarity'] < 98:
                    failed_similarity.append(labName)
                if metrics['Mean coverage depth'] == 'N/A' or float(metrics['Mean coverage depth']) < 50:
                    failed_coverage_depth.append(labName)

            # Check thresholds for user lab only if the role is not a superuser
            elif lab == user_lab:
                if metrics['coverage'] == 'N/A' or metrics['coverage'] < 0.90:
                    user_failed_coverage = True
                if metrics['coverage'] == 'N/A' or metrics['Ns'] > 2:
                    user_failed_ns = True
                if metrics['coverage'] == 'N/A' or metrics['similarity'] < 98:
                    user_failed_similarity = True
                if metrics['Mean coverage depth'] == 'N/A' or float(metrics['Mean coverage depth']) < 50:
                    user_failed_coverage_depth = True

        # Generate feedback based on role
        if role == "superuser":
            # Add summary lines for superuser
            if failed_coverage:
                doc.add_paragraph(f"Participants {', '.join(failed_coverage)} failed to satisfy the threshold for genome coverage (90%).", style='List Bullet')
            else:
                doc.add_paragraph("All participants obtained sufficient genome coverage (90% or higher).", style='List Bullet')

            if failed_ns:
                doc.add_paragraph(f"Participants {', '.join(failed_ns)} failed to satisfy the threshold for Ns in Sequence (greater than 2%).", style='List Bullet')
            else:
                doc.add_paragraph("All participants maintained Ns in Sequence within acceptable limits (2% or lower).", style='List Bullet')

            if failed_similarity:
                doc.add_paragraph(f"Participants {', '.join(failed_similarity)} failed to satisfy the threshold for Similarity (98%).", style='List Bullet')
            else:
                doc.add_paragraph("All participants obtained sufficient Similarity (98% or higher).", style='List Bullet')

            if failed_coverage_depth:
                doc.add_paragraph(f"Participants {', '.join(failed_coverage_depth)} failed to satisfy the threshold for Read Coverage (Mean depth of 50).", style='List Bullet')
            else:
                doc.add_paragraph("All participants obtained sufficient Read Coverage (Mean depth of 50 or higher).", style='List Bullet')

        else:
            # Add summary lines for non-superuser
            if user_failed_coverage:
                doc.add_paragraph("Failed to satisfy the threshold for genome coverage (90%).", style='List Bullet')
            else:
                doc.add_paragraph("Obtained sufficient genome coverage (90% or higher).", style='List Bullet')

            if user_failed_ns:
                doc.add_paragraph("Failed to satisfy the threshold for Ns in Sequence (greater than 2%).", style='List Bullet')
            else:
                doc.add_paragraph("Obtained sufficient Ns in Sequence (2% or lower).", style='List Bullet')

            if user_failed_similarity:
                doc.add_paragraph("Failed to satisfy the threshold for Similarity (98%).", style='List Bullet')
            else:
                doc.add_paragraph("Obtained sufficient Similarity (98% or higher).", style='List Bullet')

            if user_failed_coverage_depth:
                doc.add_paragraph("Failed to satisfy the threshold for Read Coverage (Mean depth of 50).", style='List Bullet')
            else:
                doc.add_paragraph("Obtained sufficient Read Coverage (Mean depth of 50 or higher).", style='List Bullet')
        
        # Add the plot image to DOCX with a caption
        doc.add_picture(plot_path, width=Inches(6))  # Adjust size as needed
        last_paragraph = doc.paragraphs[-1] 
        last_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        para = doc.add_paragraph()
        runner = para.add_run(f"Figure {str(figure_count)}. Quality metrics for sample {sample} for participants that submitted appropriate data files")
        runner.bold = True
        runner.italic = True
        last_paragraph = doc.paragraphs[-1] 
        last_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        figure_count+=1
        
        # Caption for the table
        para = doc.add_paragraph()
        para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        runner = para.add_run(f"Table {str(table_count)}. Quality metrics data for sample {sample}")
        runner.bold = True
        runner.italic = True

        # Generate and insert the metrics table for the sample
        table = doc.add_table(rows=1, cols=5)  # Creating a table with 5 columns for metrics
        table.style = 'Table Grid'

        # Adding the header row for the table
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Participant'
        hdr_cells[0].paragraphs[0].runs[0].bold = True
        hdr_cells[1].text = 'Genome Coverage (%)'
        hdr_cells[1].paragraphs[0].runs[0].bold = True
        hdr_cells[2].text = 'Ns in Sequence (%)'
        hdr_cells[2].paragraphs[0].runs[0].bold = True
        hdr_cells[3].text = 'Similarity (%)'
        hdr_cells[3].paragraphs[0].runs[0].bold = True
        hdr_cells[4].text = 'Read Coverage (Mean)'
        hdr_cells[4].paragraphs[0].runs[0].bold = True

        # Add data rows for each lab/sample entry
        labCount = 0
        for lab, metrics in data.items():
            #if lab == 'WR024':
            #    labName = 'reference'
            #else:
            #labCount += 1
            #labName = str(labCount)
            labName=lab

            # Add a new row to the table
            row_cells = table.add_row().cells

            # Fill in the cells for each column
            row_cells[0].text = labName  # First column with lab name (bold)
            row_cells[0].paragraphs[0].runs[0].italic = True  # Bold the first column

            # Coverage column (highlight if less than 90%)
            coverage_value = metrics['coverage'] * 100 if metrics['coverage']!="N/A" else "N/A"
            if metrics['coverage']!="N/A":
                row_cells[1].text = f"{coverage_value:.1f}"
                if coverage_value < 90:
                    row_cells[1].paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW  # Highlight if less than 90%
                # Ns column (highlight if higher than 2%)
                ns_value = metrics['Ns']
                row_cells[2].text = f"{ns_value:.1f}"
                if ns_value > 2:
                    row_cells[2].paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW  # Highlight if higher than 2%

                # Similarity column (highlight if less than 98%)
                similarity_value = metrics['similarity']
                row_cells[3].text = f"{similarity_value:.1f}"
                if similarity_value < 98:
                    row_cells[3].paragraphs[0].runs[0].font.highlight_color = WD_COLOR_INDEX.YELLOW  # Highlight if less than 98%

            # Mean coverage depth column
            mean_coverage_depth_value = metrics['Mean coverage depth']
            if metrics['Mean coverage depth']!="N/A":
                row_cells[4].text = f"{mean_coverage_depth_value:.1f}"

        # Increment figure and table count
        table_count += 1

        if role != "superuser":
            reference_genome = "project/static/genomes/EPI_ISL_412866/EPI_ISL_412866.fasta" if sample_reference_map[sample]=="EPI_ISL_412866" else "project/static/genomes/EPI_ISL_1653999/EPI_ISL_1653999.fasta"
            region="EPI_ISL_412866:1-15225" if sample_reference_map[sample]=="EPI_ISL_412866" else "EPI_ISL_1653999:1-15222"
            annotation = "project/static/genomes/EPI_ISL_412866/EPI_ISL_412866.gtf" if sample_reference_map[sample]=="EPI_ISL_412866" else "project/static/genomes/EPI_ISL_1653999/EPI_ISL_1653999.gtf"
            output_dir = "project/static/plots"
            print(sample)
            print(region)
            print(reference_genome)
            print(annotation)
            bigwig_file_path = os.path.join(f"data/{distribution}/{user_lab}/{sample}", f"{user_lab}_{sample}.bw")
            if os.path.exists(bigwig_file_path):
                bigwig_copy=os.path.join(output_dir,f"{user_lab}_{sample}.bw")
                shutil.copy(bigwig_file_path,bigwig_copy)
            else:
                bigwig_copy=None
            bigwig_consensus_file_path = os.path.join(f"data/{distribution}/{user_lab}/{sample}", f"{user_lab}_{sample}_consensus.bw")
            bigwig_consensus_copy=os.path.join(output_dir,f"{user_lab}_{sample}_consensus.bw")
            shutil.copy(bigwig_consensus_file_path,bigwig_consensus_copy)
            bed_path = os.path.join(f"data/{distribution}/{user_lab}/{sample}", f"{user_lab}_{sample}_mutations.bed")
            bed_path_copy=os.path.join(output_dir,f"{user_lab}_{sample}_mutations.bed")
            shutil.copy(bed_path,bed_path_copy)
            output_dir = "project/static/plots"
            plot_path = create_pygenometracks_plot( reference_genome, annotation, region, bed_path_copy, bigwig_copy, bigwig_consensus_copy, output_dir, sample, user_lab)
            
            # Add the plot image to DOCX with a caption
            doc.add_picture(plot_path, width=Inches(7.5))  # Adjust size as needed
            last_paragraph = doc.paragraphs[-1] 
            last_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            last_paragraph = doc.paragraphs[-1]
            para = doc.add_paragraph()
            runner = para.add_run(f"Figure {str(figure_count)}. Genomic visualisation of submitted sequence and reads.")
            runner.bold = True
            runner.italic = True
            last_paragraph = doc.paragraphs[-1] 
            last_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            last_paragraph.add_run().add_break(WD_BREAK.PAGE)
            figure_count+=1
        
        

       
























    # Appendixes
    appendix1=doc.add_paragraph()
    runner=appendix1.add_run(f"Appendix 1: Additional Information\n\n")
    runner.bold = True
    runner=appendix1.add_run(f"Samples provided and testing required\n")
    runner.bold = True
    runner.italic = True
    runner=appendix1.add_run(f"""Original samples distributed by UK NEQAS Microbiology were freeze dried.
 ➢  Sequencing-only laboratories received samples directly and were instructed to reconstitute with 0.5mL of
molecular grade water prior to testing.
 ➢  Samples processed by a primary testing laboratory were forwarded on as RNA / lysate and handled and
stored according to local procedures / policies.
Sequencing was carried out according to the laboratory's normal procedure.\n\n""")
    runner=appendix1.add_run(f"Data submission and analysis\n")
    runner.bold = True
    runner.italic = True
    runner=appendix1.add_run(f"""Data collection, quality control (QC), storage and analysis to  WHO defined standards and requirements was carried out by University of Cranfield in collaborations with UK NEQAS for Microbiology and Micropathology ltd.\nParticipants were required to submit FASTA, FASTQ or BAM files which are used to assess quality metrics. FASTQ files are processed preferentially over BAM files. If a FASTQ file is not provided but a BAM file is, it will realigned to reference sequence. Should a FASTA not be provided, a consensus sequence will be automatically generated from the FASTQ/BAM, otherwise the provided FASTA will be assumed to be the consensus sequence.\n\n""")
    runner=appendix1.add_run(f"Validated results\n")
    runner.bold = True
    runner.italic = True
    runner=appendix1.add_run(f"""The EQA cases were validated by a national RSV sequencing reference laboratory using Illumina sequencing with 99.9% of the genome covered at 20x. The quality of the reference laboratory sequences was classed as very high. Participants have only been assessed against regions successfully covered by the reference laboratory. Stated lineages were established using Nextclade and Nextstrain identifiers are reported. Participant submissions were compared against the reference sequences suggested by GISAID: EPI_ISL_412866 (RSV A) and EPI_ISL_1653999 (RSV B) for all regions successfully sequenced by the reference laboratory.\n\n""")
    runner=appendix1.add_run(f"Quality Metrics\n")
    runner.bold = True
    runner.italic = True
    runner = appendix1.add_run(f"""Where appropriate data files have been provided by the participant, the following quality metrics will be stated on the reports:
➢  Genome Coverage (%) - The percentage of reference bases covered, with a threshold typically set at ≥90%. Computed using Nextclade.
➢  Ns in Sequence (%) - The percentage of ambiguous bases (N's) in the sequence, with a threshold typically set at ≤2%. Computed using Nextclade.
➢  Similarity (%) - The percentage of sequence similarity compared to the reference, with a threshold typically set at ≥98%. Computed using Nextclade.
➢  Read Coverage (Mean Depth) - The average depth of sequencing reads, with a threshold typically set at ≥50. Computed using Qualimap2.\n\n""") 
    runner=appendix1.add_run(f"Participation and scoring submissions\n")
    runner.bold = True
    runner.italic = True
    runner=appendix1.add_run(f"""xxxxxxxxxxxxxxxxxx\n\n""")
    runner=appendix1.add_run(f"Scheme compliance\n")
    runner.bold = True
    runner.italic = True
    runner=appendix1.add_run(f"""All participating laboratories complied with Scheme instructions.\n\n""")

    #add generator mention
    current_year = datetime.datetime.now().year
    automention=doc.add_paragraph() 
    automention.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    rights=automention.add_run(f"\n\n\n\n\n\n\n\n\n\nAutomatically generated by xxx. All rights reserved © UKNEQAS for Microbiology; {current_year}")
    rights.bold = True
    rights.italic = True
    


    # Save the document to a BytesIO object and add footers
    docx_io = BytesIO()
    add_page_number(doc.sections[0].footer.paragraphs[0].add_run("RSV Sequencing Distributions ... Pilot EQA Summary Report\t\t"))
    doc.sections[0].footer.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.save(docx_io)
    docx_io.seek(0)
    return doc