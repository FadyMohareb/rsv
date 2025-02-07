import React from 'react';

export default function Settings() {
  return (
    <div className="page-container">
      <h1>Settings</h1>
      <p>Update your preferences here:</p>
      <form className="settings-form">
        <div className="input-group">
          <label htmlFor="notification" className="input-label">Notifications:</label>
          <select id="notification" className="input-field">
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>
        <div className="input-group">
          <label htmlFor="theme" className="input-label">Theme:</label>
          <select id="theme" className="input-field">
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
        <button type="submit" className="login-button">Save Settings</button>
      </form>
    </div>
  );
}
