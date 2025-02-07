import React, { Component } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { themeQuartz, themeBalham, themeAlpine } from 'ag-grid-community';
import SamplePlot from './SamplePlot.js';
import ScaleLoader from 'react-spinners/ScaleLoader';
import DownloadButton from './DownloadButton.js';
import { JBrowseLinearGenomeView, createViewState } from '@jbrowse/react-linear-genome-view';

class DataView extends Component {
    constructor(props) {
        super(props);
        this.state = {
            loading: true,
            distribution: '1',
            distributions: [],
            sampleDetails: {},
            sampleSelect: '',
            tableData: null,
            tracks: [],
            viewState: null,
            numParticipants: 0,
            role: this.props.role,
            loadFailed: false,  // ✅ New state to track load failures
        };

        // Bind methods
        this.handleSampleSelection = this.handleSampleSelection.bind(this);
        this.handleDistributionChange = this.handleDistributionChange.bind(this);
        this.loadSampleDetails = this.loadSampleDetails.bind(this);
        this.loadSamplePlotAndData = this.loadSamplePlotAndData.bind(this);
        this.createViewState = this.createViewState.bind(this);
    }

    componentDidMount() {
        this.fetchDistributions();
        this.createViewState([]); // Initialize the viewState with no tracks
    }
    createViewState(tracks) {
        const { sampleSelect, sampleDetails } = this.state;
        const reference = sampleDetails[sampleSelect]?.reference || 'EPI_ISL_412866'; // Default to 'EPI_ISL_412866' if no reference found

        const featureTrack = {
            trackId: `${reference}_annotations`,
            name: `${reference} Annotations`,
            type: 'FeatureTrack',
            assemblyNames: [reference],
            adapter: {
                type: 'Gff3Adapter',
                gffLocation: {
                    uri: `api/proxy_gff3_${reference}`,
                },
            },
        };

        const viewState = createViewState({
            assembly: {
                name: reference,
                aliases: [reference],
                sequence: {
                    trackId: `${reference}_reference`,
                    type: 'ReferenceSequenceTrack',
                    adapter: {
                        type: 'IndexedFastaAdapter',
                        fastaLocation: {
                            uri: `api/proxy_fasta_${reference}`,
                        },
                        faiLocation: {
                            uri: `api/proxy_fai_${reference}`,
                        },
                    },
                },
            },
            tracks: [featureTrack, ...tracks], // Include dynamic feature track
        });
        console.log(tracks)
        this.setState({ viewState });
    }


    async loadSamplePlotAndData(sample) {
        try {
            this.setState({ loading: true, loadFailed: false });
            const { sampleSelect, sampleDetails } = this.state;
            const reference = sampleDetails[sampleSelect]?.reference || 'EPI_ISL_412866'; // Default to 'EPI_ISL_412866' if no reference found

            const response = await fetch(
                `api/distribution_data/${this.state.distribution}/sample/${sample}`,
                { credentials: 'include' }
            );
            if (!response.ok) {
                throw new Error('Failed to fetch plot and table data');
            }
            const data = await response.json();

            // Interleave BAM and BigWig tracks by sample
            const tracks = [];

            // Assuming data.bams and data.bigwigs are arrays of equal length
            const numTracks = Math.max(data.bams.length, data.bigwigs.length);

            for (let i = 0; i < numTracks; i++) {
                const participant = data.bams[i].split('/').slice(-1)[0];
                if (data.bams[i]) {
                    tracks.push({
                        trackId: `bam_track_${i}`,
                        name: `${participant}`, // Customizing name for each sample
                        type: 'AlignmentsTrack',
                        assemblyNames: [reference],
                        adapter: {
                            type: 'BamAdapter',
                            bamLocation: { uri: data.bams[i] },
                            index: { location: { uri: `${data.bams[i]}.bai` } },
                        },
                        display: [
                            {
                                type: 'SnpCoverage',
                                displayId: 'bam_snp_coverage',
                                renderer: {
                                    type: 'SnpCoverageRenderer',
                                },
                            },
                        ],
                    });
                }

                if (data.bigwigs[i]) {
                    tracks.push({
                        trackId: `bigwig_track_${i}`,
                        name: `${participant} coverage`, // Customizing name for each sample
                        type: 'QuantitativeTrack',
                        assemblyNames: [reference],
                        adapter: {
                            type: 'BigWigAdapter',
                            bigWigLocation: { uri: data.bigwigs[i] },
                        },
                    });
                }
            }

            // Recreate viewState with the new BAM tracks
            this.createViewState(tracks);

            // Apply NA handling
            const sanitizedTableData = data.table?.map(row =>
                Object.fromEntries(
                    Object.entries(row).map(([key, value]) => [key, value === "N/A" ? null : value])
                )
            ) || null;

            this.setState({
                tableData: sanitizedTableData,
                tracks,
                loading: false,
            });

        } catch (error) {
            console.error('Error fetching plot and table data:', error);
            this.setState({ loading: false, loadFailed: true });
        }
    }

    // Fetch the list of distributions
    async fetchDistributions() {
        try {
            this.setState({ loading: true });
            const response = await fetch('api/create_distributions', {
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to fetch distributions');
            }

            const data = await response.json();

            // Debugging: Check the API response
            console.log("Fetched distributions:", data);

            this.setState({ loading: false }); // Set loading to false once data is fetched
            this.setState({ distributions: data.distributions, loading: false });
        } catch (error) {
            console.error('Error fetching distributions:', error);
            this.setState({ loading: false });
        }
    };

    async loadSampleDetails() {
        try {
            this.setState({ loading: true });
            const response = await fetch(`api/distribution_data/${this.state.distribution}`, {
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch sample details');
            }
            const data = await response.json();
            this.setState({ sampleDetails: data, loading: false });
        } catch (error) {
            console.error('Error fetching sample details:', error);
            this.setState({ loading: false });
        }
    }


    handleSampleSelection(sample) {
        const { sampleDetails } = this.state;
        const numParticipants = sampleDetails[sample]?.participants || 0; // ✅ Get participants count

        this.setState({
            sampleSelect: sample,
            numParticipants,  // ✅ Save in state
        }, () => {
            this.loadSamplePlotAndData(sample);
        });
    }


    handleDistributionChange(event) {
        this.setState({ distribution: event.target.value }, () => {
            this.loadSampleDetails(); // Executes after state update
        });
    }

    render() {
        const {
            loading,
            sampleDetails,
            tableData,
            distribution,
            distributions,
            viewState,
            bamTracks,
            numParticipants,
            role,
            loadFailed
        } = this.state;
        console.log(role)

        const shouldShowData = !loading && tableData && numParticipants >= 4 && !loadFailed;

        const chartOrientation = role === 'superuser' ? 'vertical' : 'horizontal'; // Determine chart orientation

        const columnDefs = [
            { field: 'participant', headerName: 'Participant', sortable: true, filter: true, minWidth: 75, maxWidth: 125, flex: 2 },
            { field: 'clade', headerName: 'Clade', sortable: true, filter: true, minWidth: 50, maxWidth: 125, flex: 1 },
            { field: 'G_clade', headerName: 'Legacy clade', sortable: true, filter: true, minWidth: 50, maxWidth: 150, flex: 1 },
            { field: 'coverage', headerName: 'Genome Coverage (%)', sortable: true, filter: true, minWidth: 50, maxWidth: 200, flex: 1 },
            { field: 'similarity', headerName: 'Similarity (%)', sortable: true, filter: true, minWidth: 50, maxWidth: 200, flex: 1 },
            { field: 'ns', headerName: 'Ns in Sequence (%)', sortable: true, filter: true, minWidth: 50, maxWidth: 200, flex: 1 },
            { field: 'read_coverage', headerName: 'Read Coverage (Mean)', sortable: true, filter: true, minWidth: 50, maxWidth: 200, flex: 1 },
        ];

        const myTheme = themeQuartz.withParams({
            backgroundColor: '#ffffff', // Matches even row background
            foregroundColor: '#1E3A5F', // Text color for the table
            headerTextColor: '#ffffff', // White header text
            headerBackgroundColor: '#1E3A5F', // Matches header background color
            oddRowBackgroundColor: '#f9f9f9', // Matches odd row background
            evenRowBackgroundColor: '#ffffff', // Matches even row background
            headerColumnResizeHandleColor: '#f1f1f1', // Subtle hover color for headers
        });

        return (
            <div className="dataview-container">
                {/* Left Panel */}
                <div className="left-panel panel">
                    <div className="input-box" id="distribution-container">
                        <label htmlFor="distribution" className="label">Distribution Number</label>
                        <select
                            id="distribution"
                            value={distribution}
                            onChange={this.handleDistributionChange}
                            className="select-input"
                        >
                            <option value="">-- Select Distribution --</option>
                            {distributions.map((dist, index) => (
                                <option key={index} value={dist}>
                                    {dist}
                                </option>
                            ))}
                        </select>

                        {/* Button to Download DOCX */}
                        <DownloadButton distribution={distribution} disabled={numParticipants < 4} />
                    </div>

                    <div className="table-container" id="sample-table-container">
                        <table className="sample-table">
                            <thead>
                                <tr>
                                    <th>Sample Name</th>
                                    <th>Reference</th>
                                    <th>Number of Participants</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(sampleDetails).map(([sample, details]) => (
                                    <tr
                                        key={sample}
                                        onClick={() => this.handleSampleSelection(sample)}
                                        className="sample-row"
                                    >
                                        <td>{sample}</td>
                                        <td>{details.reference === 'EPI_ISL_1653999' ? 'RSV B' : 'RSV A'}</td>
                                        <td>{details.participants}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <div style={{ width: '100%', height: '475px', overflow: 'scroll' }}>
                        {viewState && <JBrowseLinearGenomeView viewState={viewState} />}
                    </div>
                </div>

                {/* Right Panel */}
                <div className="right-panel panel">
                    {shouldShowData ? (
                        <>
                            <div className={`plot-container ${loading || !tableData ? 'hidden' : ''}`} id="plot-container">
                                {loading ? (
                                    <div className="spinner">
                                        <ScaleLoader color="#21afde" />
                                    </div>
                                ) : (
                                    <SamplePlot sampleData={tableData} chartOrientation={chartOrientation} />
                                )}
                            </div>

                            <div className={`table-container ${loading || !tableData ? 'hidden' : ''}`} id="table-container" style={{ width: '100%', overflowX: 'auto' }}>
                                {loading ? (
                                    <div className="spinner">
                                        <ScaleLoader color="#21afde" />
                                    </div>
                                ) : (
                                    tableData && (
                                        <div style={{ width: '100%', height: '350px' }}>
                                            <AgGridReact
                                                rowData={tableData}
                                                columnDefs={columnDefs}
                                                defaultColDef={{
                                                    sortable: true,
                                                    filter: true,
                                                    resizable: true,
                                                }}
                                                theme={myTheme}
                                                domLayout="normal"
                                            />
                                        </div>
                                    )
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="error-message">
                            Insufficient participant data
                        </div>
                    )}
                </div>
            </div>

        );


    }
}

export default DataView;