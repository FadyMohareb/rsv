/**
 * Renders a form for uploading sequencing data files along with associated metadata,
 * handles file changes and form submission with progress tracking, and fetches required
 * data (user organization, distributions, and samples) from the API.
 * @module Upload
 * @memberof App
 * @returns {JSX.Element} The rendered upload page.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import InteractiveTooltip from './InteractiveTooltip'; // Adjust the path as needed

export default function Upload() {
    const navigate = useNavigate(); // Create a navigation function
    const [fasta, setFasta] = useState(null); // State for the FASTA file
    const [bam, setBam] = useState(null); // State for the BAM file
    const [fq1, setFastq1] = useState(null); // State for the FASTQ R1 file
    const [fq2, setFastq2] = useState(null); // State for the FASTQ R2 file
    const [description, setDescription] = useState(''); // State for the description text
    const [distribution, setDistribution] = useState(''); // State for the selected distribution
    const [distributions, setDistributions] = useState([]); // State for fetched distributions
    const [sampleDetails, setSampleDetails] = useState([]); // State for sample details
    const [sampleSelect, setSampleSelect] = useState(''); // State for selected sample
    const [sequencingType, setSequencingType] = useState('');
    const [organization, setOrganization] = useState(''); // State for the user's organization
    const [loading, setLoading] = useState(false); // State for loading indicator
    const [samplesLoading, setSamplesLoading] = useState(false); // State for loading samples
    const [uploadProgress, setUploadProgress] = useState(0); // State for upload progress

    /**
    * Fetches the logged-in user's organization from the API.
    * @async
    * @returns {Promise<void>}
    */
    const fetchUserOrganization = async () => {
        try {
            const response = await fetch('api/user', { credentials: 'include' });
            if (response.ok) {
                const data = await response.json();
                setOrganization(data.organization); // Set the organization state
            } else {
                console.error('Failed to fetch user organization');
            }
        } catch (error) {
            console.error('Error fetching user organization:', error);
        }
    };

    /**
    * Fetches the list of distributions from the API and updates state.
    * @async
    * @returns {Promise<void>}
    */
    const fetchDistributions = async () => {
        try {
            setLoading(true); // Set loading to true while fetching data
            const response = await fetch('api/distribution_fetch', {
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to fetch distributions');
            }

            const data = await response.json();
            setDistributions(data.distributions || []); // Set the distributions into state
            setLoading(false); // Set loading to false once data is fetched
        } catch (error) {
            console.error('Error fetching distributions:', error);
            setLoading(false); // Set loading to false in case of error
        }
    };

    /**
    * Fetches samples for the selected distribution from the API.
    * @async
    * @param {string} selectedDistribution - The selected distribution.
    * @returns {Promise<void>}
    */
    const fetchSamplesForDistribution = async (selectedDistribution) => {
        if (!selectedDistribution) return;

        try {
            setSamplesLoading(true); // Set loading for samples
            const response = await fetch(
                `api/distributions/${selectedDistribution}/samples`,
                { credentials: 'include' }
            );

            if (!response.ok) {
                throw new Error('Failed to fetch samples for distribution');
            }

            const data = await response.json();
            setSampleDetails(data.samples || []); // Set the samples for the distribution
            setSamplesLoading(false); // Set loading for samples to false
        } catch (error) {
            console.error(`Error fetching samples for distribution '${selectedDistribution}':`, error);
            setSamplesLoading(false); // Set loading for samples to false
        }
    };

    // Load user organization and distributions on component mount
    useEffect(() => {
        fetchUserOrganization(); // Fetch the organization
        fetchDistributions(); // Fetch the distributions
    }, []); // Only run once on mount

    /**
    * Handles changes to the FASTA file input.
    * @param {Event} event - The file input change event.
    * @returns {void}
    */
    const handleFastaChange = (event) => {
        setFasta(event.target.files[0]);
    };

    /**
     * Handles changes to the BAM file input.
     * @param {Event} event - The file input change event.
     * @returns {void}
     */
    const handleBamChange = (event) => {
        setBam(event.target.files[0]);
    };

    /**
    * Handles changes to the FASTQ R1 file input.
    * @param {Event} event - The file input change event.
    * @returns {void}
    */
    const handleFastq1Change = (event) => {
        setFastq1(event.target.files[0]);
    };
    /**
    * Handles changes to the FASTQ R2 file input.
    * @param {Event} event - The file input change event.
    * @returns {void}
    */
    const handleFastq2Change = (event) => {
        setFastq2(event.target.files[0]);
    };

    /**
    * Handles changes to the sequencing type input.
    * @param {Event} event - The change event.
    * @returns {void}
    */
    const handleSequencingTypeChange = (event) => {
        setSequencingType(event.target.value);
    };

    /**
       * Handles changes to the description input.
       * @param {Event} event - The change event.
       * @returns {void}
       */
    const handleDescriptionChange = (event) => {
        setDescription(event.target.value);
    };

    /**
    * Handles changes to the distribution selector.
    * Fetches the samples for the newly selected distribution.
    * @param {Event} event - The change event.
    * @returns {void}
    */
    const handleDistributionChange = (event) => {
        const selectedDistribution = event.target.value;
        setDistribution(selectedDistribution);

        // Fetch samples for the selected distribution
        fetchSamplesForDistribution(selectedDistribution);
    };

    /**
    * Handles sample selection from the dropdown.
    * Updates state with the selected sample and number of participants, then loads sample plot and data.
    * @param {Event} event - The selection change event.
    * @returns {void}
    */
    const handleSampleSelection = (event) => {
        setSampleSelect(event.target.value);
    };

    /**
    * Handles form submission for uploading files.
    * Creates a FormData object with files and metadata, sends it via XMLHttpRequest,
    * and tracks upload progress. Navigates to home upon success.
    * @param {Event} event - The form submit event.
    * @returns {void}
    */
    const handleSubmit = (event) => {
        event.preventDefault();

        // Show confirmation dialog before proceeding
        const userConfirmed = window.confirm(
            "Uploading  will remove all previously existing data for this sample. Proceed?"
        );

        if (!userConfirmed) {
            return; // Stop submission if user cancels
        }

        // Create a FormData object to hold the files and other form data
        const formData = new FormData();
        if (fasta) formData.append('fasta', fasta); // Add FASTA file if present
        if (bam) formData.append('bam', bam); // Add BAM file if present
        if (fq1) formData.append('fq1', fq1); // Add FASTQ R1 file if present
        if (fq2) formData.append('fq2', fq2); // Add FASTQ R2 file if present
        formData.append('description', description); // Add description, even if it's empty
        formData.append('sample', sampleSelect);
        formData.append('distribution', distribution);
        formData.append('organization', organization); // Include the fetched organization
        formData.append('sequencing_type', sequencingType); // Include the sequencing type
        console.log('sequencing_type', sequencingType);

        // Create a new XMLHttpRequest to send the form data
        const xhr = new XMLHttpRequest();

        // Set up the request
        xhr.open('POST', 'api/upload', true);
        xhr.setRequestHeader('Accept', 'application/json');
        setLoading(true)

        // Ensure credentials (such as cookies) are included with the request
        xhr.withCredentials = true;

        // Track progress and update state
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                setUploadProgress(percentComplete); // Update the progress bar state
            }
        });

        // Handle when the request is complete
        xhr.onload = () => {
            if (xhr.status === 201) {
                alert('File(s) uploaded successfully!');
                navigate('/'); // Navigate back to home page after successful upload
            } else {
                let errorData;
                try {
                    errorData = JSON.parse(xhr.responseText);
                } catch (e) {
                    console.error("Failed to parse JSON:", xhr.responseText);
                    errorData = { error: "Unknown error" };
                }
                alert(`Failed to upload files: ${errorData.error}`);
            }
            setLoading(false); // Hide the loading spinner after the upload completes
        };

        // Handle network errors
        xhr.onerror = () => {
            console.error('Error uploading file');
            alert('An error occurred while uploading. Please try again.');
            setLoading(false); // Hide the loading spinner in case of an error
        };

        // Send the form data
        xhr.send(formData);
    };

    return (
        <div className="page-container">
            <h1>Upload Sequencing Data</h1>

            {/* Instructions list */}
            <br />
            <strong>Instructions</strong>
            <br />
            <ol>
                <li>Choose the corresponding distribution and sample you wish to upload data for.</li>
                <li>All files are <strong>optional</strong>.</li>
                <li>Uploaded files will <strong>overwrite</strong> those provided previously.</li>
            </ol>
            <br />

            {/* File upload form */}
            <form onSubmit={handleSubmit}>
                {/* Distribution Dropdown */}
                <div className="input-group">
                    <label htmlFor="distribution"
                        className="input-label"
                    ><InteractiveTooltip tooltipText="Choose the distribution associated with the sample you wish to upload data for. (Required)" /> Distribution<span style={{ color: '#b83030' }}>*</span>
                        </label>
                    <select
                        id="distribution"
                        value={distribution}
                        onChange={handleDistributionChange}
                        className="input-field"
                        disabled={loading} // Disable dropdown while loading
                        required

                    >
                        <option value="">Select Distribution</option>
                        {loading ? (
                            <option value="">Loading distributions...</option>
                        ) : (
                            distributions.map((dist) => (
                                <option key={dist} value={dist}>
                                    {dist}
                                </option>
                            ))
                        )}
                    </select>
                </div>

                {/* Sample Dropdown */}
                <div className="input-group">
                    <label htmlFor="sample" className="input-label"><InteractiveTooltip tooltipText="Select the ID of the sample to be uploaded. (Required)" /> Sample<span style={{ color: '#b83030' }}>*</span>
                        
                    </label>
                    <select
                        id="sample"
                        value={sampleSelect}
                        onChange={handleSampleSelection}
                        className="input-field"
                        disabled={samplesLoading} // Disable dropdown while loading samples
                        required
                    >
                        <option value="">Select Sample</option>
                        {samplesLoading ? (
                            <option value="">Loading samples...</option>
                        ) : (
                            sampleDetails.map((sample) => (
                                <option key={sample} value={sample}>
                                    {sample}
                                </option>
                            ))
                        )}
                    </select>
                </div>
                {/* Sequencing Type Input with Autocompletion */}
                <div className="input-group">
                    <label htmlFor="sequencingType" className="input-label">
                    <InteractiveTooltip tooltipText="Type in the name of the sequencing platform used for analysis. (Required)" /> Sequencing Platform<span style={{ color: '#b83030' }}>*</span>
                    </label>
                    <input
                        type="text"
                        id="sequencingType"
                        value={sequencingType}
                        onChange={handleSequencingTypeChange}
                        className="input-field"
                        required
                        list="sequencingOptions"
                    />
                    <datalist id="sequencingOptions">
                        <option value="Real-Time Single Target" />
                        <option value="CDC:RSV_RUO-01 mpx" />
                        <option value="Allplex SARS, FluA/B, RSV" />
                        <option value="Altona: RealStar" />
                        <option value="Real-Time Multiplex" />
                        <option value="Luminex: NxTAG Resp." />
                        {/* Add or modify options as needed, although this could be improved by fetching options from API */}
                    </datalist>
                </div>
                {/* FASTA File Input */}
                <div className="input-group">
                    <label htmlFor="fasta" className="input-label"><InteractiveTooltip tooltipText="FASTA file with the consensus sequence of the sample. Only one entry is expected, known gaps can be included using N character. Can be compressed with gzip." /> FASTA File</label>
                    <input
                        type="file"
                        id="fasta"
                        onChange={handleFastaChange}
                        className="input-field"
                    />
                </div>

                {/* BAM File Input */}
                <div className="input-group">
                    <label htmlFor="bam" className="input-label"><InteractiveTooltip tooltipText="BAM file with the aligned reads. These will be realigned to Nextclade's suggested reference sequence. " /> BAM File</label>
                    <input
                        type="file"
                        id="bam"
                        onChange={handleBamChange}
                        className="input-field"
                    />
                </div>

                {/* FASTQ R1 File Input */}
                <div className="input-group">
                    <label htmlFor="fq1" className="input-label"><InteractiveTooltip tooltipText="FASTQ file with paired end R1 reads, or single end reads. Can be compressed wi " /> FASTQ R1 File</label>
                    <input
                        type="file"
                        id="fq1"
                        onChange={handleFastq1Change}
                        className="input-field"
                    />
                </div>

                {/* FASTQ R2 File Input */}
                <div className="input-group">
                    <label htmlFor="fq2" className="input-label">FASTQ R2 File</label>
                    <input
                        type="file"
                        id="fq2"
                        onChange={handleFastq2Change}
                        className="input-field"
                    />
                </div>

                {/* Description Input */}
                <div className="input-group">
                    <label htmlFor="description" className="input-label"> <InteractiveTooltip tooltipText="Currently unused. " /> Description</label>
                    <textarea
                        id="description"
                        value={description}
                        onChange={handleDescriptionChange}
                        className="input-field"
                    ></textarea>
                </div>

                {/* Loading and Progress Bar */}
                {
                    loading && (
                        <div className="loading-spinner">
                            <p>Uploading...</p>
                            <div className="progress-bar-container">
                                <div className="progress-bar" style={{ width: `${uploadProgress}%` }}></div>
                            </div>
                        </div>
                    )
                }

                {/* Submit Button */}
                <div className="input-group">
                    <button type="submit" className="login-button" disabled={loading}>
                        {loading ? 'Uploading...' : 'Submit'}
                    </button>
                </div>
            </form >
        </div >
    );
}
