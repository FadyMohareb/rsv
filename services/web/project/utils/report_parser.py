import numpy as np
import os
import csv

import os
import csv

def parse_nextclade_file(nextclade_file_path, nextclade_alternative_file_path, genomeLength):
    """Parses Nextclade output and calculates uniformity based on coverage and mutations."""
    
    if not os.path.isfile(nextclade_file_path):
        print(f"Warning: Nextclade file missing: {nextclade_file_path}")
        return {
            'seqName': 'N/A', 'coverage': 'N/A', 'totalMissing': 'N/A', 'Ns': 'N/A',
            'substitutions': 'N/A', 'deletions': 'N/A', 'insertions': 'N/A',
            'frameShifts': 'N/A', 'similarity': 'N/A', 'clade': 'N/A', 'G_clade': 'N/A', 'subtype': 'N/A'
        }
    
    # Initialize the score from alternative if provided, default to None if not provided
    score_alternative = None

    if nextclade_alternative_file_path and os.path.isfile(nextclade_alternative_file_path):
        try:
            with open(nextclade_alternative_file_path, 'r') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    score_alternative = float(row.get('qc.overallScore', 0))  # Use 0 as default if key is missing
        except Exception as e:
            print(f"Error processing alternative file {nextclade_alternative_file_path}: {e}")
            score_alternative = None

    subtype = 'unknown'  # Default subtype is unknown
    
    with open(nextclade_file_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            try:
                score = float(row.get('qc.overallScore', 0))  # Default to 0 if missing or invalid

                # Logic to compare scores
                if score_alternative is not None:
                    if score < score_alternative:
                        subtype = "original"
                    elif score > score_alternative:
                        subtype = "alternative"
                    else:
                        subtype = "unknown"  # If scores are equal, mark as unknown
                else:
                    # If no alternative file, default to original
                    subtype = "original" if score > 0 else "unknown"

                # Calculate other necessary values
                coverage = float(row['coverage'])
                total_missing = int(row['totalMissing'])
                alignment_start = int(row['alignmentStart'])
                alignment_end = int(row['alignmentEnd'])
                alignment_length = alignment_end - alignment_start
                
                substitutions = int(row['totalSubstitutions'])
                deletions = int(row['totalDeletions'])
                insertions = int(row['totalInsertions'])
                frame_shifts = int(row['totalFrameShifts'])

                clade = row.get('clade', 'N/A')
                g_clade = row.get('G_clade', 'N/A')

                adjusted_coverage = alignment_length - total_missing - substitutions - deletions - insertions - frame_shifts
                similarity = adjusted_coverage / genomeLength

                return {
                    'seqName': row['seqName'],
                    'coverage': coverage,
                    'totalMissing': total_missing,
                    'Ns': total_missing / genomeLength * 100,
                    'substitutions': substitutions,
                    'deletions': deletions,
                    'insertions': insertions,
                    'frameShifts': frame_shifts,
                    'similarity': similarity * 100,
                    'clade': clade,
                    'G_clade': g_clade,
                    'subtype': subtype
                }
            except Exception as e:
                print(f"Error processing Nextclade file {nextclade_file_path}: {e}")
                return {
            'seqName': 'N/A', 'coverage': 'N/A', 'totalMissing': 'N/A', 'Ns': 'N/A',
            'substitutions': 'N/A', 'deletions': 'N/A', 'insertions': 'N/A',
            'frameShifts': 'N/A', 'similarity': 'N/A', 'clade': 'N/A', 'G_clade': 'N/A', 'subtype': 'N/A'
        }

def parse_qualimap(genome_results_path, coverage_histogram_path):
    """ Parses Qualimap genome_results.txt and coverage histogram file. """

    if not os.path.isfile(genome_results_path) or not os.path.isfile(coverage_histogram_path):
        print(f"Warning: Missing Qualimap files ({genome_results_path} or {coverage_histogram_path})")
        return {
            "Coverage at 20X (%)": 'N/A',
            "Mean coverage depth": 'N/A',
            "Standard deviation of coverage depth": 'N/A',
            "Read depth (Median)": 'N/A',
            "Uniformity (%)": 'N/A'
        }

    metrics = {}

    with open(genome_results_path, 'r') as f:
        for line in f:
            if "There is a" in line and "of reference with a coverageData >= 20X" in line:
                metrics["Coverage at 20X (%)"] = float(line.split()[3].strip('%'))

            if "mean coverageData" in line:
                metrics["Mean coverage depth"] = float(line.split("=")[1].strip().replace(",", "").replace("X", ""))

            if "std coverageData" in line:
                metrics["Standard deviation of coverage depth"] = float(line.split("=")[1].strip().replace(",", "").replace("X", ""))

    try:
        histogram_data = np.loadtxt(coverage_histogram_path, skiprows=1)
        depths = histogram_data[:, 0]
        counts = histogram_data[:, 1]
        total_locations = np.sum(counts)

        cumulative_counts = np.cumsum(counts)
        median_index = np.searchsorted(cumulative_counts, total_locations / 2)
        metrics["Read depth (Median)"] = depths[median_index]

        threshold = 0.1 * metrics["Read depth (Median)"]
        uniform_bases = np.sum(counts[depths >= threshold])
        metrics["Uniformity (%)"] = (uniform_bases / total_locations) * 100
    except Exception as e:
        print(f"Error processing Qualimap histogram: {e}")
        metrics["Read depth (Median)"] = 'N/A'
        metrics["Uniformity (%)"] = 'N/A'

    return metrics

def read_genome_length(sample_path):
    """ Reads genome length from genomeLength.txt, handling missing file cases. """
    genome_length_file = os.path.join(sample_path, "genomeLength.txt")
    if os.path.isfile(genome_length_file):
        try:
            with open(genome_length_file, 'r') as f:
                return int(f.read().strip())
        except ValueError:
            print(f"Warning: Invalid genomeLength.txt format in {sample_path}")
            return None
    else:
        print(f"Warning: genomeLength.txt not found in {sample_path}")
        return None

def process_all_reports(base_dir):
    """ Processes all samples in the given directory and extracts relevant metrics. """

    report_data = {}

    for lab in os.listdir(base_dir):
        lab_path = os.path.join(base_dir, lab)
        if os.path.isdir(lab_path):
            report_data[lab] = {}
            for sample in os.listdir(lab_path):
                sample_path = os.path.join(lab_path, sample)
                if os.path.isdir(sample_path):
                    genome_results_path = os.path.join(sample_path, "genome_results.txt")
                    coverage_histogram_path = os.path.join(sample_path, "raw_data_qualimapReport/coverage_histogram.txt")
                    nextclade_file_path = os.path.join(sample_path, "nextclade.output")
                    nextclade_alternative_file_path = os.path.join(sample_path, "nextclade_alternative.output")

                    # Read genome length
                    genome_length = read_genome_length(sample_path)
                    if genome_length is None:
                        continue  # Skip if genome length is missing

                    report_data[lab][sample] = {
                        'fasta': os.path.join(sample_path, f"{lab}_{sample}.fasta"),
                        'bam': os.path.join(sample_path, f"{lab}_{sample}.bam"),
                        'bai': os.path.join(sample_path, f"{lab}_{sample}.bam.bai"),
                    }

                    # Process Qualimap data
                    qualimap_metrics = parse_qualimap(genome_results_path, coverage_histogram_path)
                    report_data[lab][sample].update(qualimap_metrics)

                    # Process Nextclade data
                    nextclade_metrics = parse_nextclade_file(nextclade_file_path, nextclade_alternative_file_path, genome_length)
                    report_data[lab][sample].update(nextclade_metrics)

    return report_data
