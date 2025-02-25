/**
 * @module DownloadButtonAll
 * @memberof DataView
 * @description Renders a button to download a DOCX report for a specified distribution.
 *
 * @param {Object} props - Component properties.
 * @param {string} props.distribution - Distribution identifier for the report.
 * @param {boolean} props.disabled - Flag to disable the button.
 * @returns {JSX.Element} The rendered download button.
 */

import React, { useState } from 'react';

const DownloadButtonAll = ({ distribution, organization, disabled }) => {
   /**
   * Handles file download by fetching the report from the API and triggering a download.
   *
   * @async
   */
    const [loading, setLoading] = useState(false);

    const handleDownload = async () => {
        if (disabled) return; // Prevent execution if disabled

        try {
            setLoading(true);
            const response = await fetch(`api/download_docx_all/${distribution}`, {
                method: 'GET',
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error('Failed to download the file');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `MIC_${organization}_All_Report.zip`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (error) {
            console.error('Error downloading the file:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleDownload}
            className="upload-button"
            style={{ marginLeft: "90px", width: "170px", opacity: disabled ? 0.5 : 1, cursor: disabled ? "not-allowed" : "pointer" }}
            disabled={loading || disabled} // Disable when loading or explicitly disabled
        >
            {loading ? 'Downloading...' : 'Download All'}
        </button>
    );
};

export default DownloadButtonAll;
