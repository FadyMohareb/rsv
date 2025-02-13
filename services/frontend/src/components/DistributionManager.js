import React, { useState, useEffect } from "react";
import axios from "axios";

const DistributionManager = () => {
  const [organizations, setOrganizations] = useState([]);
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

  // assignments is an object: { participantName: { distributionName: true/false } }
  const [assignments, setAssignments] = useState({});

  useEffect(() => {
    fetchDistributionsAndOrganizations(); // Fetch data on mount
  }, []);

  const fetchDistributionsAndOrganizations = async () => {
    try {
      const response = await fetch("api/distributions_participants", {
        credentials: "include",
      });
      const data = await response.json();

      // Extract distribution names from the distributions list.
      // Each distribution has: id, name, samples, and organizations.
      const distroNames = (data.distributions || []).map((dist) => dist.name);
      setDistributions(distroNames);

      // Set organizations list
      setOrganizations(data.organizations || []);

      // Parse assignments mapping from distributions.
      // Expected structure: { organizationName: { distributionName: true } }
      const assignmentsMapping = {};
      (data.distributions || []).forEach((dist) => {
        // For each organization assigned to the distribution...
        (dist.organizations || []).forEach((org) => {
          if (!assignmentsMapping[org.name]) {
            assignmentsMapping[org.name] = {};
          }
          // Mark that this organization is assigned to this distribution.
          assignmentsMapping[org.name][dist.name] = true;
        });
      });
      setAssignments(assignmentsMapping);
    } catch (error) {
      setMessage("Failed to load distributions and organizations.");
      setMessage2("Failed to load distributions and organizations.");
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
      formData.append("name", newDistribution);
      const response = await fetch("api/create_distributions", {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (response.ok) {
        setMessage(
          "The new distribution " + newDistribution + " was registered."
        );
        setDistributions([...distributions, newDistribution]);
        setNewDistribution("");
      } else {
        alert("Error creating distribution. Please try again.");
        setMessage("Error creating distribution. Please try again.");
      }
    } catch (error) {
      setMessage("Error creating distribution. Please try again.");
      console.error("Error creating distribution:", error);
      alert("Error creating distribution. Please try again.");
    }
  };

  const addSampleToDistribution = async () => {
    if (!selectedDistribution || !sample.trim() || !selectedRSV) {
      setMessage2(
        "Please select a distribution, provide a sample name, and choose an RSV type."
      );
      return;
    }

    const formData = new FormData();
    formData.append("sample", sample);
    formData.append("rsv_type", selectedRSV); // Include RSV type

    try {
      const response = await fetch(
        `api/distributions/${selectedDistribution}/samples`,
        {
          method: "POST",
          body: formData,
          credentials: "include",
        }
      );

      if (response.ok) {
        setMessage2(
          `The new sample ${sample} with RSV type ${selectedRSV} was added to ${selectedDistribution}`
        );
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
    if (
      !organizationName.trim() ||
      !organizationEmail.trim() ||
      !organizationUsername.trim()
    ) {
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
        setOrganizations((prevOrganizations) => [
          ...prevOrganizations,
          organizationName,
        ]);
      } else {
        const errorData = await response
          .json()
          .catch(() => ({ error: "An unknown error occurred." }));
        setMessage3(errorData.error || "An error occurred. Please try again.");
      }
    } catch (error) {
      console.error("Error during organization action:", error);
      setMessage3(
        "An error occurred while processing your request. Please try again."
      );
    }
  };

  const toggleAssignment = async (participant, distribution) => {
    // If already assigned, do nothing
    if (assignments[participant] && assignments[participant][distribution]) {
      return;
    }

    // Alert the user that the assignment is permanent
    const confirmed = window.confirm(
      "This assignment is permanent. Are you sure you want to assign?"
    );

    if (!confirmed) return;

    try {
      // Send assignment data to the backend
      const response = await fetch("api/assign_participant", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          participant,
          distribution,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to assign participant. Please try again.");
      }

      // Update the frontend state only if the API request succeeds
      setAssignments((prevAssignments) => {
        const newAssignments = { ...prevAssignments };
        if (!newAssignments[participant]) {
          newAssignments[participant] = {};
        }
        newAssignments[participant][distribution] = true;
        return newAssignments;
      });

      setMessage("Participant successfully assigned.");
    } catch (error) {
      console.error("Error assigning participant:", error);
      setMessage("An error occurred. Please try again.");
    }
  };


  return (
    <div className="page-container" style={{ width: "920px" }}>
      <h1>Management Dashboard</h1>

      <div className="grid-container">
        {/* Create Distribution Section */}
        <section className="grid-item" style={{ height: "360px" }}>
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
          </div>
          <div className="input-group">
            <button className="action-button" onClick={createDistribution}>
              Create Distribution
            </button>
          </div>
          {message && <div className="message-box">{message}</div>}
        </section>

        {/* Add Sample to Distribution Section */}
        <section className="grid-item" style={{ height: "360px" }}>
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
          </div>
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
          <div className="input-group">
            <button className="action-button" onClick={addSampleToDistribution}>
              Add Sample
            </button>
          </div>
          {message2 && <div className="message-box">{message2}</div>}
        </section>

        {/* Organization Manager Section */}
        <section className="grid-item">
          <h2>Organization Manager</h2>
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
          <div className="input-group">
            <button className="action-button" onClick={handleOrganizationAction}>
              {isRestoreMode ? "Restore Password" : "Create Organization"}
            </button>
          </div>
          {message3 && <div className="message-box">{message3}</div>}
        </section>

        <section className="grid-item">
          <h2>Distribution Assignment</h2>
          <div style={{
            overflowX: "auto",
            overflowY: "auto",
            maxHeight: "500px", // Limits height to enable vertical scrolling
            maxWidth: "100%"
          }}>
            <table
              className="assignment-table"
              style={{
                width: "100%",
                borderCollapse: "collapse",
                tableLayout: "fixed",
                minWidth: "400px", // Ensures columns don’t get too narrow
              }}
            >
              <thead>
                <tr>
                  <th style={{
                    border: "1px solid #ddd",
                    padding: "5px",
                    fontSize: "14px",
                    minWidth: "80px", // Prevents excessive shrinking
                    maxWidth: "150px", // Constrains width
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    position: "sticky",
                    top: 0,
                    backgroundColor: "#fff", // Keeps header visible when scrolling
                    zIndex: 2
                  }}>
                    Organization
                  </th>
                  {distributions.map((dist, idx) => (
                    <th key={idx} style={{
                      border: "1px solid #ddd",
                      padding: "5px",
                      fontSize: "14px",
                      minWidth: "80px",
                      maxWidth: "150px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      position: "sticky",
                      top: 0,
                      backgroundColor: "#fff",
                      zIndex: 2
                    }}>
                      {dist}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {organizations.map((org, pIndex) => (
                  <tr key={pIndex}>
                    <td style={{
                      border: "1px solid #ddd",
                      padding: "5px",
                      fontSize: "14px",
                      minWidth: "80px",
                      maxWidth: "150px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      wordWrap: "break-word",
                      position: "sticky",
                      left: 0, // Keeps first column fixed
                      backgroundColor: "#fff", // Ensures visibility
                      zIndex: 1 // Ensures it stays on top
                    }}>
                      {org}
                    </td>
                    {distributions.map((dist, dIndex) => {
                      const isAssigned = assignments[org] && assignments[org][dist];
                      return (
                        <td
                          key={dIndex}
                          className="assignment-cell"
                          style={{
                            border: "1px solid #ddd",
                            padding: "5px",
                            minWidth: "50px",
                            maxWidth: "100px",
                            textAlign: "center",
                            cursor: "pointer",
                            backgroundColor: isAssigned ? "#4CAF50" : "#fff",
                            color: isAssigned ? "#fff" : "#000",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                          onClick={() => toggleAssignment(org, dist)}
                        >
                          {isAssigned ? "✓" : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};

export default DistributionManager;
