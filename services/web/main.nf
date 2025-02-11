// Read and parse the samples.txt file into a map (dictionary-like structure)
def samples_map = [:]

params.ref="project/static/genomes/"
params.reads="data/RSV 2024 Winter/**/*/" //"data/RSV 2024 Winter/**/*/*_R1.fastq*"
params.samples_txt="data/RSV 2024 Winter/samples.txt"

// Read the samples.txt file line by line
new File(params.samples_txt).eachLine { line ->
    def (sample, reference) = line.trim().split(/\s+/)  // Split the line into sample and reference
    if (sample && reference) {
        samples_map[sample] = reference  // Populate the map
    } else {
        throw new Exception("Invalid line in samples.txt: $line")  // Handle invalid lines
    }
}

// println "Parsed samples map: ${samples_map}"  // Debugging: view the parsed map
process extractReadsFromBam {
    cache 'lenient'
    input:
    tuple val(sample_id), path(bam_file), path(outputdir)

    output:
    tuple file("${outputdir}/${sample_id}_R1.fastq.gz"), file("${outputdir}/${sample_id}_R2.fastq.gz"), path(outputdir), val(sample_id)

    script:
    """
    # Check if the BAM file contains paired-end data
    paired_reads=\$(samtools view -c -f 1 "$bam_file")
    
    # If paired-end data is present, extract both R1 and R2
    if [ "\$paired_reads" -gt 0 ]; then
        samtools sort -n "$bam_file" | samtools fastq -1 ${outputdir}/${sample_id}_R1.fastq.gz -2 ${outputdir}/${sample_id}_R2.fastq.gz
    else
        # If it's single-end data, extract only R1
        samtools sort -n "$bam_file" | samtools fastq -0 ${outputdir}/${sample_id}_R1.fastq.gz
        touch ${outputdir}/${sample_id}_R2.fastq.gz
    fi

    
    """
}


process bbdukTrim {
    cache 'lenient'
    input:
    tuple path(reads1), path(reads2), path(outputdir), val(sample_id)  // Input R1, R2

    output:
    path("${outputdir}/${sample_id}_R*_trimmed.fastq.gz"), emit: trimmed
    path(outputdir), emit: outputdir

    script:
    """
    # Check if reads2 exists and is not empty
    if [ ! -s "$reads2" ]; then
        # Single-end trimming
        /bbmap/bbduk.sh in="$reads1" out="${outputdir}/${sample_id}_R1_trimmed.fastq.gz" ktrim=r k=23 mink=11 ref=adapters qtrim=rl trimq=20 tpe tbo
    else
        # Paired-end trimming
        /bbmap/bbduk.sh in1="$reads1" in2="$reads2" out1="${outputdir}/${sample_id}_R1_trimmed.fastq.gz" out2="${outputdir}/${sample_id}_R2_trimmed.fastq.gz" ktrim=r k=23 mink=11 ref=adapters qtrim=rl trimq=20 tpe tbo
    fi
    """
}
// Process: Align FASTA files to the reference genome
process alignFastas {
    cache 'lenient'
    input:
    tuple val(sample_id), path(fasta_file), path(outputdir), path(reference)

    output:
    path("${outputdir}/${sample_id}_consensus.bam"), emit: consensus_bam
    path("${outputdir}/${sample_id}_consensus.bw"), emit: consensus_bw

    script:
    """
    /usr/bin/minimap2  -a "${reference}" "${fasta_file}" | \
    /usr/bin/samtools sort -o "${outputdir}/${sample_id}_consensus.bam"
    /usr/bin/samtools index "${outputdir}/${sample_id}_consensus.bam"
    bamCoverage --bam "${outputdir}/${sample_id}_consensus.bam" --outFileName "${outputdir}/${sample_id}_consensus.bw" --outFileFormat bigwig
    """
}


process alignReads {
    cache 'lenient'
    input:
    tuple val(sample_id), path(reference), path(trimmed_reads)
    path(outputdir)

    output:
    tuple val(sample_id), path(outputdir), path("${outputdir}/${sample_id}.bam") // Save BAM files in the output directory

    script:
    def idxbase = reference[0].baseName

    // Separate R1 and R2 from trimmed_reads array
    def (r1, r2) = trimmed_reads.size() == 2 ? trimmed_reads : [trimmed_reads[0], null] // Handle single-end and paired-end cases

    // Run BWA MEM based on whether R2 exists
    if (r2) {
        """
        bwa mem "${idxbase}" "$r1" "$r2" | /usr/bin/samtools sort -o "${outputdir}/${sample_id}.bam"
        samtools index "${outputdir}/${sample_id}.bam"
        """
    } else {
        """
        bwa mem "${idxbase}" "$r1" | /usr/bin/samtools sort -o "${outputdir}/${sample_id}.bam"
        samtools index "${outputdir}/${sample_id}.bam"
        """
    }
}


process qualimapQC {
    cache 'lenient'
    input:
    tuple path (bam_file), path (outputdir)

    output:
    path("${outputdir}")  // Save the Qualimap output in a subdirectory

    script:
    """
    /opt/qualimap/qualimap bamqc -bam "$bam_file" -outdir "${outputdir}"
    """
}

process generateConsensus {
    cache 'lenient'
    input:
    tuple val(sample_id), path(bam_file), path(index_file), path(outputdir)

    output:
    tuple val(sample_id), path("${outputdir}/${sample_id}.fasta"), path(outputdir)

    script:
    """
    samtools mpileup -aa -A -d 0 -Q 0 "$bam_file" | \
    ivar consensus -p "${outputdir}/${sample_id}" -m 10
    mv "${outputdir}/${sample_id}.fa" "${outputdir}/${sample_id}.fasta"
    """
}

process nextclade {
    cache 'lenient'
    input:
    tuple val(sample_id), path(fasta_file), path(outputdir), val(dataset) // Input the sample ID, FASTA file, and output directory

    output:
    path("${outputdir}/nextclade.output"), emit: report // Save Nextclade report in output directory

    script:
    """
    nextclade run \
        --dataset-name "${dataset}" \
        --output-tsv "${outputdir}/nextclade.output" \
        "$fasta_file"
    """
}

// New nextclade process for alternative reference
process nextcladeAlternative {
    cache 'lenient'
    input:
    tuple val(sample_id), path(fasta_file), path(outputdir), val(dataset) // Input the sample ID, FASTA file, and output directory

    output:
    path("${outputdir}/nextclade_alternative.output"), emit: alternative_report // Save Nextclade report for the alternative dataset

    script:
    """
    # Switch dataset value based on the condition
    if [ "${dataset}" == "nextstrain/rsv/a/EPI_ISL_412866" ]; then
        nextclade run \
            --dataset-name nextstrain/rsv/b/EPI_ISL_1653999 \
            --output-tsv "${outputdir}/nextclade_alternative.output" \
            "$fasta_file"
    elif [ "${dataset}" == "nextstrain/rsv/b/EPI_ISL_1653999" ]; then
        nextclade run \
            --dataset-name nextstrain/rsv/a/EPI_ISL_412866 \
            --output-tsv "${outputdir}/nextclade_alternative.output" \
            "$fasta_file"
    fi
    """
}


process bamToBigWig {
    cache 'lenient'
    input:
    tuple val(sample_id), path(bam_file), path(index_file), path(outputdir)  // Tuple input: BAM file, index file, and output directory

    output:
    path("${outputdir}/${bam_file.baseName}.bw"), emit: bigwig  // Emit the BigWig file

    script:
    """
    # Generate BigWig file from BAM and its index
    bamCoverage --bam "$bam_file" --outFileName "${outputdir}/${bam_file.baseName}.bw" --outFileFormat bigwig
    """
}


workflow {
    // Get all BAMs
    bam_samples = Channel
        .fromPath("${params.reads}*_original.bam")  // Fetch BAM files
        .map { bam_file ->              
            def sample = bam_file.parent.name  // Extract sample name from folder structure
            def sample_id = "${bam_file.parent.parent.name}_${bam_file.parent.name}"
            def outputdir = bam_file.parent  // Extract output directory

            // Try to find the corresponding fastq file, excluding 'trimmed' files
            def fastq_file = file("${params.reads}${bam_file.parent.parent.name}_${bam_file.parent.name}_original_R1.fastq*")
                 .find { it.name.contains('_original_R1') && !it.name.contains('trimmed') }

            if (fastq_file) {
                null
            } else {
                [sample_id, bam_file, outputdir]
            }
        }
        .filter { it != null }  // Remove the null values (those that have FASTQs)
        .set { bam_input }

    // bam_input.view()

    // Extract reads from BAM only for missing samples
    generated_fastqs = extractReadsFromBam(bam_input)

    // Fetch R1 and R2 files, ensuring correct handling of references, and exclude files with 'trimmed' in their names
    fastq_files = Channel
        .fromPath("${params.reads}*_original_R1.fastq*")  // Fetch R1 files
        .filter { r1_file -> 
            !r1_file.name.contains('trimmed')  // Exclude files with 'trimmed' in their names
        }
        .map { r1_file -> 
            def sample = r1_file.parent.name  // Extract sample name from folder structure
            def sample_id = "${r1_file.parent.parent.name}_${r1_file.parent.name}"

            // Try to find the corresponding R2 file, excluding 'trimmed' files
            def r2_file = file("${params.reads}${r1_file.parent.parent.name}_${r1_file.parent.name}_original_R2.fastq*")
                 .find { it.name.contains('_original_R2') && !it.name.contains('trimmed') }

            // If R2 exists, pair R1 and R2 with output directory
            if (r2_file) {
                [r1_file, r2_file, r1_file.parent,sample_id]
            } else {
                [r1_file, file("NO_FILE"), r1_file.parent,sample_id]
            }
        }.view { it -> "Fastqs: $it" }

    // Debugging before merging
    //generated_fastqs.view { it -> "Generated FASTQs: $it" }
    //fastq_files.view { it -> "Existing FASTQs: $it" }

    // Correct merging
    merged_fastqs = fastq_files.concat(generated_fastqs)

    // Debug merged fastq_files
    //merged_fastqs.view { it -> "Merged FASTQ tuple: $it" }

    // Proceed with the pipeline
    bbdukTrim(merged_fastqs)

    // Condense channel operations
    def aligned_inputs = bbdukTrim.out.trimmed.map { trimmed ->
        // Handle both single file and tuple cases
        def filePath = trimmed instanceof List ? trimmed[0] : trimmed
        def sample_id = filePath.baseName.replaceFirst('_R1.*', '')

        // Extract reference based on sample ID
        def reference = file("${params.ref}${samples_map[sample_id.split('_')[1]]}/${samples_map[sample_id.split('_')[1]]}.fasta.{,amb,ann,bwt,pac,sa}")

        // Prepare trimmed reads for alignment
        def trimmed_reads = trimmed instanceof List && trimmed.size() == 2 
            ? trimmed  // Paired-end reads
            : [filePath]  // Single-end reads

        // Return tuple of all required values
        tuple(sample_id, reference, trimmed_reads)
    }

    // Pass the aligned_inputs channel to alignReads
    // aligned_inputs.view()
    aligned = alignReads(aligned_inputs,bbdukTrim.out.outputdir)

    // Run Qualimap QC on each BAM file
    aligned.map { tuple ->
        def (sample_id, outputdir, bam_path) = tuple  
        [bam_path, outputdir]  // Separate BAM file and its output directory
    } | qualimapQC

    // Prepare BAM and index files for BigWig generation
    bam_files = aligned.map { tuple ->
        def (sample_id, outputdir, bam_path) = tuple 
        def index_file = file("${bam_path}.bai")  // Locate the index file for the BAM
        if (!index_file.exists()) {
            throw new Exception("Index file not found for BAM: ${bam_path}")
        }
        [sample_id, bam_path, index_file, outputdir]  // Tuple of BAM file, index file, and output directory
    }

    bamToBigWig(bam_files)

    // Nextclade fastas with reference fetching
    fasta_files = Channel
        .fromPath("${params.reads}*_original.fasta")  // Fetch FASTA files
        .map { fasta_file ->
            def sample = fasta_file.parent.name  // Extract sample name from folder structure
            def sample_id = "${fasta_file.parent.parent.name}_${fasta_file.parent.name}"
            def reference = file("${params.ref}${samples_map[sample]}/${samples_map[sample]}.fasta")  // Fetch reference files
            def dataset = samples_map[sample] == 'EPI_ISL_412866'
                ? "nextstrain/rsv/a/EPI_ISL_412866"
                : "nextstrain/rsv/b/EPI_ISL_1653999"
            [sample_id, fasta_file, fasta_file.parent, dataset, reference]  // Include reference in the tuple
        }
        //.view { it -> "Fastas: $it" }

    missing_consensus = bam_files
    .map { bam_tuple -> 
        def (sample_id, bam_path, index_file, outputdir) = bam_tuple
        def fasta_file = file("${outputdir}/${sample_id}_original.fasta")
        
        // Check if the FASTA file exists and contains '_original' in its name
        if (fasta_file.exists() && fasta_file.name.contains('_original')) {
            return null  // If FASTA exists, return null (no need to include this sample)
        } else {
            return [sample_id, bam_path, index_file, outputdir]  // If FASTA does not exist, return the sample tuple
        }
    }
    .filter { it != null }  // Remove null values (samples with existing FASTA)
    //.view { it -> "Missing fasta tuple: $it" }  // View the missing FASTA samples  

    // Generate FASTA consensus for missing samples
    generated_consensus = generateConsensus(missing_consensus)

    // Add reference & dataset to generated FASTAs
    generated_consensus_with_meta = generated_consensus.map { tuple ->
        def (sample_id, fasta_file, outputdir) = tuple
        def reference = file("${params.ref}${samples_map[sample_id.split('_')[1]]}/${samples_map[sample_id.split('_')[1]]}.fasta")
        def dataset = samples_map[sample_id.split('_')[1]] == 'EPI_ISL_412866'
            ? "nextstrain/rsv/a/EPI_ISL_412866"
            : "nextstrain/rsv/b/EPI_ISL_1653999"
        [sample_id, fasta_file, outputdir, dataset, reference] // Add reference & dataset
    }.view { it -> "Generated fastas: $it" }

    final_fasta_files = fasta_files.concat(generated_consensus_with_meta)
    final_fasta_files.view()
    
    // Send to Nextclade process
    nextclade(final_fasta_files.map { tuple -> tuple[0..3] })  // Use only fasta_file, outputdir, and dataset for Nextclade
    nextcladeAlternative(final_fasta_files.map { tuple -> tuple[0..3] }) // Alternative Nextclade run

    // Send to Align Fastas process
    alignFastas(final_fasta_files.map { tuple ->
        def (sample_id, fasta_file, outputdir, _, reference) = tuple  // Extract relevant fields
        println "Reference: ${reference}"  // Print reference
        [sample_id, fasta_file, outputdir, reference]
    })
}