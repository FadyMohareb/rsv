import React from 'react';
import Plot from 'react-plotly.js';

const SeqPlot = ({ sampleData, chartOrientation }) => {
  if (!sampleData) return <div>Loading plot...</div>;

    // Helper function to safely parse numeric values, replacing "N/A", null, or undefined with 0
    const safeParse = (value) => (value === "N/A" || value == null ? null : Number(value));

    // Extract and clean data
    const anonymizedLabs = sampleData.map((row) => `${row.sequencing_type} (${row.count})`);
    const genomeCoveragePercent = sampleData.map((row) => safeParse(row.coverage));
    const numNsPercent = sampleData.map((row) => safeParse(row.ns));
    const similarityPercent = sampleData.map((row) => safeParse(row.similarity));
    const readCoverage = sampleData.map((row) => safeParse(row.read_coverage));

  const isHorizontal = chartOrientation === 'horizontal';

  const barCoverage = {
    x: isHorizontal ? genomeCoveragePercent : anonymizedLabs,
    y: isHorizontal ? anonymizedLabs : genomeCoveragePercent,
    type: 'bar',
    orientation: isHorizontal ? 'h' : 'v',
    name: 'Genome Coverage (%)',
    marker: { color: '#1E3A5F' },
    opacity: 0.8,
  };

  const barNs = {
    x: isHorizontal ? numNsPercent : anonymizedLabs,
    y: isHorizontal ? anonymizedLabs : numNsPercent,
    type: 'bar',
    orientation: isHorizontal ? 'h' : 'v',
    name: 'Ns in Sequence (%)',
    marker: { color: '#FBC02D' },
    opacity: 0.8,
  };

  const barSimilarity = {
    x: isHorizontal ? similarityPercent : anonymizedLabs,
    y: isHorizontal ? anonymizedLabs : similarityPercent,
    type: 'bar',
    orientation: isHorizontal ? 'h' : 'v',
    name: 'Similarity (%)',
    marker: { color: '#F57C00' },
    opacity: 0.8,
  };

  const lineReadCoverage = {
    x: isHorizontal ? readCoverage : anonymizedLabs,
    y: isHorizontal ? anonymizedLabs : readCoverage,
    type: 'scatter',
    mode: 'lines+markers',
    name: 'Read Coverage (Mean)',
    line: { color: 'black', width: 2 },
    ...(isHorizontal ? { xaxis: 'x2' } : { yaxis: 'y2' }), // Dynamically adjust axis
  };

  const verticalLayout = {
    height:350,
    margin: {
      t: 30, // Remove top margin (reduce space above the plot)
      r: 40, // Reduce right margin
      b: 70, // Reduce bottom margin
      l: 40, // Reduce left margin
    },
    xaxis: {
      title: 'Participant',
    },
    barmode:'group',
    yaxis: {
      title: 'Percentage (%)',
      side: 'left',
      showgrid: true,
      range: [
        0,
        100,
      ],
    },
    yaxis2: {
      title: 'Read Coverage (Mean)',
      side: 'right',
      overlaying: 'y', // Aligns the second y-axis with the first
      showgrid: false,
      range: [0, Math.max(...readCoverage) * 1.1],
    },
    shapes: [
      // Horizontal line at 2%
      {
        type: 'line',
        x0: -1,
        y0: 2,
        x1: anonymizedLabs.length,
        y1: 2,
        line: { color: '#FBC02D', width: 2, dash: 'dash' }, // Red dashed line at 2%
      },
      // Horizontal line at 90%
      {
        type: 'line',
        x0: -1,
        y0: 90,
        x1: anonymizedLabs.length,
        y1: 90,
        line: { color: '#1E3A5F', width: 2, dash: 'dash' }, // Green dashed line at 90%
      },
      // Horizontal line at 98%
      {
        type: 'line',
        x0: -1,
        y0: 98,
        x1: anonymizedLabs.length,
        y1: 98,
        line: { color: '#F57C00', width: 2, dash: 'dash' }, // Blue dashed line at 98%
      },
      // Horizontal line at 50 read coverage of yaxis2
      {
        type: 'line',
        x0: -1,
        y0: 50,
        x1: anonymizedLabs.length,
        y1: 50,
        line: { color: 'black', width: 2, dash: 'dash' }, // Black dashed line at 50% of yaxis2
        yref: 'y2', // This specifies that the line should be placed on yaxis2
      },
    ],
    legend: {
      x: 0.5,
      y: -0.2,
      orientation: 'h', // Legend below the plot
    },
  };

  const horizontalLayout = {
    margin: {
      t: 30, // Remove top margin (reduce space above the plot)
      r: 30, // Reduce right margin
      b: 40, // Reduce bottom margin
      l: 40, // Reduce left margin
    },
    xaxis: {
      title: 'Percentage (%)',
      range: [0, 100],
    },
    yaxis: {
      title: 'Participant',
      automargin: true,
    },
    xaxis2: {
      title: 'Read Coverage (Mean)',
      overlaying: 'x',
      side: 'top',
      range: [0, Math.max(...readCoverage) * 1.1],
    },
    barmode: 'group',
    shapes: [
      { type: 'line', x0: 2, y0: -1, x1: 2, y1: anonymizedLabs.length, line: { color: '#FBC02D', dash: 'dash' } },
      { type: 'line', x0: 90, y0: -1, x1: 90, y1: anonymizedLabs.length, line: { color: '#1E3A5F', dash: 'dash' } },
      { type: 'line', x0: 98, y0: -1, x1: 98, y1: anonymizedLabs.length, line: { color: '#F57C00', dash: 'dash' } },
      { type: 'line', x0: 50, y0: -1, x1: 50, y1: anonymizedLabs.length, xref: 'x2', line: { color: 'black', dash: 'dash' } },
    ],
    legend: { x: 0.5, y: -0.2, orientation: 'h' },
  };

  const plotData = isHorizontal
  ? [barNs, barSimilarity, barCoverage, lineReadCoverage] // Reversed order
  : [barCoverage, barSimilarity, barNs, lineReadCoverage]; // Original order

  return (
    <div className="plot-container">
      <Plot data={plotData} layout={chartOrientation === 'horizontal' ? horizontalLayout:verticalLayout } />
    </div>
  );
};

export default SeqPlot;
