import React, { useState } from 'react';

const DownloadButton = ({ distribution, disabled }) => {
    const [loading, setLoading] = useState(false);

    const handleDownload = async () => {
        if (disabled) return; // Prevent execution if disabled

        try {
            setLoading(true);
            const response = await fetch(`api/download_docx/${distribution}`, {
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
            a.download = `${distribution}.docx`;
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
            {loading ? 'Downloading...' : 'Download Report'}
        </button>
    );
};

export default DownloadButton;
