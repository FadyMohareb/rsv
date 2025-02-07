import React, { useState, useEffect } from "react";
import axios from "axios";

const DistributionManager = () => {
  const [distributions, setDistributions] = useState([]);
  const [newDistribution, setNewDistribution] = useState("");
  const [sample, setSample] = useState("");
  const [selectedDistribution, setSelectedDistribution] = useState("");
  const [message, setMessage] = useState("");
  const [message2, setMessage2] = useState("");
  const [message3, setMessage3] = useState("");
  const [selectedRSV, setSelectedRSV] = useState(""); // RSV Selection State
  const [isRestoreMode, setIsRestoreMode] = useState(false); 

  // State for new organization
  const [organizationName, setOrganizationName] = useState("");
  const [organizationEmail, setOrganizationEmail] = useState("");
  const [organizationUsername, setOrganizationUsername] = useState("");

  useEffect(() => {
    fetchDistributions(); // Fetch existing distributions on mount
  }, []);

  const fetchDistributions = async () => {
    try {
      const response = await fetch("api/create_distributions", {
        credentials: 'include',
      });
      const data = await response.json();
      setDistributions(data.distributions || []);
    } catch (error) {
      setMessage("Failed to load distributions.");
      setMessage2("Failed to load distributions.");
    }
  };

  const handleRSVChange = (rsvType) => {
    setSelectedRSV(rsvType === selectedRSV ? "" : rsvType);
  };

  const createDistribution = async () => {
    if (!newDistribution.trim()) {
      setMessage("Distribution name cannot be empty.");
      return;
    }

    try {
      const formData = new FormData();
      formData.append('name', newDistribution);
      const response = await fetch('api/create_distributions', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (response.ok) {
        setMessage("The new distribution " + newDistribution + " was registered.");
        setDistributions([...distributions, newDistribution]);
        setNewDistribution("");
      } else {
        alert('Error creating distribution. Please try again.');
        setMessage("Error creating distribution. Please try again.");
      }
    } catch (error) {
      setMessage("Error creating distribution. Please try again.");
      console.error('Error creating distribution:', error);
      alert('Error creating distribution. Please try again.');
    }
  };

  const addSampleToDistribution = async () => {
    if (!selectedDistribution || !sample.trim() || !selectedRSV) {
      setMessage2("Please select a distribution, provide a sample name, and choose an RSV type.");
      return;
    }

    const formData = new FormData();
    formData.append("sample", sample);
    formData.append("rsv_type", selectedRSV); // Include RSV type

    try {
      const response = await fetch(`api/distributions/${selectedDistribution}/samples`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (response.ok) {
        setMessage2(`The new sample ${sample} with RSV type ${selectedRSV} was added to ${selectedDistribution}`);
        setSample("");
        setSelectedRSV(""); // Reset RSV selection
      } else {
        setMessage2("Error adding sample to distribution. Please try again.");
      }
    } catch (error) {
      setMessage2("Error adding sample to distribution. Please try again.");
      console.error("Error:", error);
    }
  };

  const handleOrganizationAction = async () => {
    // Validate required inputs
    if (!organizationName.trim() || !organizationEmail.trim() || !organizationUsername.trim()) {
      setMessage3("Please fill out all fields.");
      return;
    }
  
    // Email validation (simple regex)
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailPattern.test(organizationEmail)) {
      setMessage3("Please enter a valid email address.");
      return;
    }
  
    try {
      // Prepare form data for API call
      const formData = new FormData();
      formData.append("name", organizationName);
      formData.append("email", organizationEmail);
      formData.append("username", organizationUsername);
      formData.append("restore", isRestoreMode ? "true" : "false"); // Indicate the mode (create or restore)
  
      const endpoint = "api/create_or_restore_organization";
  
      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
        credentials: "include",
      });
  
      if (response.ok) {
        const responseData = await response.json();
        setMessage3(responseData.message); // Display success message from the server
        setOrganizationName("");
        setOrganizationEmail("");
        setOrganizationUsername("");
      } else {
        const errorData = await response.json().catch(() => ({ error: "An unknown error occurred." }));
        setMessage3(errorData.error || "An error occurred. Please try again.");
      }
    } catch (error) {
      console.error("Error during organization action:", error);
      setMessage3("An error occurred while processing your request. Please try again.");
    }
  };
  

  return (
    <div className="page-container">
      <h1>Distribution Manager</h1>

      {/* Create Distribution */}
      <section className="distribution-section distribution-manager-container">
        <h2>Create New Distribution</h2>
        <div className="input-group">
          <label>Distribution Name:</label>
          <input
            type="text"
            value={newDistribution}
            onChange={(e) => setNewDistribution(e.target.value)}
            placeholder="Enter distribution name"
            required
          />
          <button className="action-button" onClick={createDistribution}>
            Create Distribution
          </button>
        </div>
      </section>
      {/* Message Display */}
      {message && <div className="message-box">{message}</div>}

      {/* Add Sample to Distribution */}
      <section className="distribution-section distribution-manager-container">
        <h2>Add Sample to Distribution</h2>
        <div className="input-group">
          <label>Select Distribution:</label>
          <select
            value={selectedDistribution}
            onChange={(e) => setSelectedDistribution(e.target.value)}
          >
            <option value="">-- Select Distribution --</option>
            {distributions.map((dist, index) => (
              <option key={index} value={dist}>
                {dist}
              </option>
            ))}
          </select>
        </div>
        <div className="input-group">
          <label>Sample Name:</label>
          <input
            type="text"
            value={sample}
            onChange={(e) => setSample(e.target.value)}
            placeholder="Enter sample name"
            required
          />

          {/* RSV Type Selection */}
        <div className="input-group">
          <label>RSV Type:</label>
          <div>
            <label>
              <input
                type="checkbox"
                checked={selectedRSV === "RSV-A"}
                onChange={() => handleRSVChange("RSV-A")}
              />
              RSV-A
            </label>
            <label style={{ marginLeft: "10px" }}>
              <input
                type="checkbox"
                checked={selectedRSV === "RSV-B"}
                onChange={() => handleRSVChange("RSV-B")}
              />
              RSV-B
            </label>
          </div>
        </div>


          <button className="action-button" onClick={addSampleToDistribution}>
            Add Sample
          </button>
        </div>
      </section>
      {/* Message Display */}
      {message2 && <div className="message-box">{message2}</div>}

      {/* Create Organization Section */}
            {/* Create Organization or Restore Password Section */}
            <section className="distribution-section distribution-manager-container">
        <h2>Organization manager</h2>
        <div className="input-group">
          <label>
            <input
              type="checkbox"
              checked={isRestoreMode}
              onChange={(e) => setIsRestoreMode(e.target.checked)}
            />
            Restore Password
          </label>
        </div>
        <div className="input-group">
          <label>Organization Name:</label>
          <input
            type="text"
            value={organizationName}
            onChange={(e) => {
              const valueWithoutSpaces = e.target.value.replace(/\s+/g, "");
              setOrganizationName(valueWithoutSpaces);
            }}
            placeholder="Enter organization name"
            required
          />
        </div>
        <div className="input-group">
          <label>Email:</label>
          <input
            type="email"
            value={organizationEmail}
            onChange={(e) => setOrganizationEmail(e.target.value)}
            placeholder="Enter organization email"
            required
          />
        </div>
        <div className="input-group">
          <label>Username:</label>
          <input
            type="text"
            value={organizationUsername}
            onChange={(e) => setOrganizationUsername(e.target.value)}
            placeholder="Enter organization username"
            required
          />
        </div>
        <button className="action-button" onClick={handleOrganizationAction}>
          {isRestoreMode ? "Restore Password" : "Create Organization"}
        </button>
      </section>

      {/* Message Display */}
      {message3 && <div className="message-box">{message3}</div>}
    </div>
  );
};

export default DistributionManager;
