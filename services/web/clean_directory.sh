#!/bin/bash

DIR="$1"  # First argument is the top-level directory path

# Check if directory exists
if [[ ! -d "$DIR" ]]; then
    echo "Error: Directory '$DIR' does not exist."
    exit 1
fi

# Loop through subdirectories inside the top-level directory
for participant_dir in "$DIR"/*/; do
    if [[ -d "$participant_dir" ]]; then
        for sample_dir in "$participant_dir"*/; do
            if [[ -d "$sample_dir" ]]; then
                # Remove unwanted files in the subdirectories
                find "$sample_dir" -type f ! -name "*.fasta" ! -name "*_R1.fastq.gz" ! -name "*_R2.fastq.gz" ! -name "*_R1.fastq" ! -name "*_R2.fastq" ! -name "genomeLength.txt" -print -delete
                echo "Removed unwanted files from: $sample_dir"
                
                # Remove 'genomeResults.txt' from subdirectories (not the final directory)
                for sub_dir in "$sample_dir"*/; do
                    if [[ -d "$sub_dir" ]]; then
                        # Remove 'genomeResults.txt' from subdirectories (not the final directory)
                        find "$sub_dir" -type f -name "genomeLength.txt" -print -delete
                        echo "Removed 'genomeLength.txt' from: $sub_dir"
                    fi
                done

                # Rename the remaining files (fasta and fastq.gz or fastq) to include "_original"
                for file in "$sample_dir"/*; do
                    if [[ -f "$file" ]]; then
                        if [[ "$file" =~ \.fasta$ ]]; then
                            mv "$file" "${file%.fasta}_original.fasta"
                            echo "Renamed FASTA: $file to ${file%.fasta}_original.fasta"
                        elif [[ "$file" =~ _R1\.fastq\.gz$ ]]; then
                            mv "$file" "${file%_R1.fastq.gz}_original_R1.fastq.gz"
                            echo "Renamed FASTQ (gz): $file to ${file%_R1.fastq.gz}_original_R1.fastq.gz"
                        elif [[ "$file" =~ _R2\.fastq\.gz$ ]]; then
                            mv "$file" "${file%_R2.fastq.gz}_original_R2.fastq.gz"
                            echo "Renamed FASTQ (gz): $file to ${file%_R2.fastq.gz}_original_R2.fastq.gz"
                        elif [[ "$file" =~ _R1\.fastq$ ]]; then
                            mv "$file" "${file%_R1.fastq}_original_R1.fastq"
                            echo "Renamed FASTQ: $file to ${file%_R1.fastq}_original_R1.fastq"
                        elif [[ "$file" =~ _R2\.fastq$ ]]; then
                            mv "$file" "${file%_R2.fastq}_original_R2.fastq"
                            echo "Renamed FASTQ: $file to ${file%_R2.fastq}_original_R2.fastq"
                        fi
                    fi
                done

                # Remove empty directories in the sample directories
                find "$sample_dir" -type d -empty -print -delete
                echo "Removed empty directories from: $sample_dir"
            fi
        done
    fi
done

echo "Cleanup and renaming complete."

