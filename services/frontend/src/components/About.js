/**
 * @module About
 * 
 * @description About page component. Renders a simple About page with details about the app and version information.
 * @returns {JSX.Element} The rendered About page.
 */

import React from 'react';

export default function About() {
  return (
    <div className="page-container">
      <h1>About</h1>
      <p>Development version of UK NEQAS sequencing data management app.</p>
      <p>Version: 0.0.1</p>
    </div>
  );
}
