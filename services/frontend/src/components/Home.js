import React from 'react';
import { useNavigate } from 'react-router-dom'; // Import the useNavigate hook

export default function Home() {
  const navigate = useNavigate(); // Create a navigation function
  const SUBDIRECTORY=process.env.REACT_APP_SUBDIRECTORY_NAME || ""
  
  return (
    <div className="page-container">
      <h1> Welcome to the Home Page</h1>
      <p>This is the main dashboard where you can access the data view.</p>
      
      {/* Button to navigate to DataView */}
      <button 
        onClick={() => navigate(`${SUBDIRECTORY}/dataview`)}  style ={{width:'30%', align:'left'}}
        className="upload-button"
      >
        Go to DataView
      </button>
    </div>
  );
}
