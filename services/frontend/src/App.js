/**
 * @module App
 * 
 * @description Main application component, React-based. Manages user authentication, routing, and layout rendering. WARNING: React classes are considered legacy code now, and using functional components is preferred. Nevertheless, this class might help bring up to speed developers that are new to React but familiar with OOP, by explaining how React's state and rendering works.
 */

import React, { Component } from 'react';
import './App.css';
import DataView from './components/DataView.js';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Home from './components/Home';
import Upload from './components/Upload';
import About from './components/About';
import Settings from './components/Settings';
import DistributionManager from './components/DistributionManager.js';
import Toolbar from './components/Toolbar';  // Import Toolbar component

import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community';

// Register all Community features for AG grid table
ModuleRegistry.registerModules([AllCommunityModule]);

const jbrowseStyle = {
  paddingTop: '10px',
  paddingBottom: '10px',
  margin: '8px',
  border: '1px solid lightgray'
};

/**
 * Main application component that handles authentication and routing.
 *
 * @extends Component
 */
class App extends Component {
  /**
   * Initializes the App component and sets the initial state.
   *
   * @param {Object} props - Component properties.
   */
  constructor(props) {
    super(props);
    this.state = {
      loading: true,
      loggedIn: false,
      username: '',
      password: '',
      organization: '',
      email: '',
      loginError: '',
      oldPassword: '', // Added state for old password
      newPassword: '',
      confirmPassword: '',
      passwordError: '',
      passwordSuccess: '',
      tableData: null,
      distribution: '1',
      sampleSelect: '',
      windowWidth: window.innerWidth, // Track window width
      fastas: [],
      sampleDetails: {},
      role: '',
      windowWidth: window.innerWidth, // Track window width
      minWidth: 768, // Minimum width for the app
    };

    // Bind methods
    this.handleLogin = this.handleLogin.bind(this);
    this.handleLogout = this.handleLogout.bind(this);
    this.handleResize = this.handleResize.bind(this);
    this.handlePasswordChange = this.handlePasswordChange.bind(this);
  }

  
  /**
   * Lifecycle method that runs when the component mounts.
   * Checks login status and adds event listener for window resize.
   */
  componentDidMount() {
    this.checkLoginStatus();

    // Add resize event listener
    window.addEventListener('resize', this.handleResize);
  }
  /**
   * Lifecycle method that runs when the component unmounts.
   * Removes event listener for window resize.
   */
  componentWillUnmount() {
    // Remove the resize event listener
    window.removeEventListener('resize', this.handleResize);
  }
  /**
   * Updates window width state when resized.
   */
  handleResize() {
    // Update the window width in the state
    this.setState({ windowWidth: window.innerWidth });
  }
  /**
   * Checks the user's login status by making an API call.
   * Updates state accordingly.
   * @async
   */
  async checkLoginStatus() {
    try {
      const response = await fetch('api/user', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        this.setState({ loggedIn: true, loginError: '', role: data.role, email: data.email });
      }
    } catch (error) {
      console.error('Error checking login status:', error);
    }
  }
  /**
   * Handles user login by sending credentials to API.
   * @param {Event} event - Form submit event.
   * @async
   */
  async handleLogin(event) {
    event.preventDefault();
    const { username, password } = this.state;

    try {
      const response = await fetch('api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: new URLSearchParams({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        this.setState({ loggedIn: true, loginError: '', role: data.role, email: data.email, organization: data.organization || '' });
      } else {
        this.setState({ loginError: 'Invalid username or password', role: '', email:'' });
      }
    } catch (error) {
      console.error('Error during login:', error);
      this.setState({ loginError: 'An error occurred. Please try again.', role: '', email:'', organization: '' });
    }
  }
  /**
   * Handles user logout by making an API call.
   * @async
   */
  async handleLogout() {
    try {
      const response = await fetch('api/logout', {
        method: 'POST',
        credentials: 'include',
      });
  
      if (response.ok) {
        const SUBDIRECTORY=process.env.REACT_APP_SUBDIRECTORY_NAME || ""
        this.setState(
          { loggedIn: false, role: '', email: '' },
          () => {
            window.location.href = `${SUBDIRECTORY}/`; // Redirect to home
          }
        );
      } else {
        console.error("Logout failed");
      }
    } catch (error) {
      console.error("Error during logout:", error);
    }
  }
    /**
   * Handles user password change by verifying the old password and updating to a new password.
   * @param {Event} event - The form submit event.
   * @async
   */
  async handlePasswordChange(event) {
    event.preventDefault();
    const { oldPassword, newPassword, confirmPassword } = this.state;

    if (newPassword !== confirmPassword) {
      this.setState({ passwordError: 'Passwords do not match', passwordSuccess: '' });
      return;
    }

    try {
      // Verify old password
      const response = await fetch('api/verify_old_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: new URLSearchParams({ oldPassword }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({ error: 'Invalid response from server' }));
        this.setState({ passwordError: data.error || 'Old password is incorrect', passwordSuccess: '' });
        return;
      }

      // Change password
      const changePasswordResponse = await fetch('api/change_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: new URLSearchParams({ newPassword, oldPassword }),
      });

      if (changePasswordResponse.ok) {
        this.setState({
          passwordSuccess: 'Password changed successfully!',
          passwordError: '',
          password: newPassword
        }, () => {
          // Login again with the new password
          alert("Password changed successfully! Log in with your new password...")
          this.handleLogout();
        });
      } else {
        const data = await changePasswordResponse.json().catch(() => ({ error: 'Invalid response from server' }));
        this.setState({ passwordError: data.error || 'An error occurred while changing the password.', passwordSuccess: '' });
      }
    } catch (error) {
      console.error('Error during password change:', error);
      this.setState({ passwordError: 'An error occurred. Please try again.', passwordSuccess: '' });
    }
  }



  /**
   * Renders the login form when the user is not authenticated.
   * @returns {JSX.Element} The login form element.
   */
  renderLoginForm() {
    const { username, password, loginError } = this.state;

    return (
      <div className="login-form-container">
        <form className="login-form" onSubmit={this.handleLogin}>
          <h2 className="form-title">Login</h2>

          {loginError && <div className="error-message">{loginError}</div>}

          <div className="input-group">
            <label htmlFor="username" className="input-label">Username:</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => this.setState({ username: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div className="input-group">
            <label htmlFor="password" className="input-label">Password:</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => this.setState({ password: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <button type="submit" className="login-button">Login</button>

          <div className="footer">
            <p style={{ textAlign: "left" }}>
              To restore password, please<br />
              contact <a href="mailto:admin@example.com">admin</a>.
            </p>
          </div>
        </form>
      </div>
    );
  }
    /**
   * Renders the password change form.
   * @returns {JSX.Element} The password change form element.
   */
  renderPasswordChange() {
    const { oldPassword, newPassword, confirmPassword, passwordError, passwordSuccess } = this.state;

    return (
      <div className="page-container">
        <form className="password-change-form" onSubmit={this.handlePasswordChange}>
          <h2 className="form-title">Change Password</h2>

          {passwordError && <div className="error-message">{passwordError}</div>}
          {passwordSuccess && <div className="success-message">{passwordSuccess}</div>}

          <div className="input-group">
            <label htmlFor="oldPassword" className="input-label">Old Password:</label>
            <input
              id="oldPassword"
              type="password"
              value={oldPassword}
              onChange={(e) => this.setState({ oldPassword: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div className="input-group">
            <label htmlFor="newPassword" className="input-label">New Password:</label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => this.setState({ newPassword: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <div className="input-group">
            <label htmlFor="confirmPassword" className="input-label">Confirm Password:</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => this.setState({ confirmPassword: e.target.value })}
              required
              className="input-field"
            />
          </div>

          <button type="submit" className="change-password-button">Change Password</button>
        </form>
      </div>
    );
  }

  /**
   * Renders the main application when the user is logged in.
   * @returns {JSX.Element} The main application layout with routing.
   */
  renderApp() {
    const { role, email, windowWidth, organization } = this.state;
    const SUBDIRECTORY=process.env.REACT_APP_SUBDIRECTORY_NAME || ""
    console.log(SUBDIRECTORY);
    
    return (
      <Router>
        <div className="app-container">
          {/* Toolbar - Replaced inline code with the Toolbar component */}
          <Toolbar role={role} email={email} handleLogout={this.handleLogout} />



          <div className="routes-container" style={{ display: 'flex', width: '100%' }}>
            <Routes>
              <Route path={`${SUBDIRECTORY}/`} element={<Home />} />
              <Route path={`${SUBDIRECTORY}/upload`} element={<Upload />} />
              <Route path={`${SUBDIRECTORY}/about`} element={<About />} />
              <Route path={`${SUBDIRECTORY}/settings`} element={<Settings />} />
              <Route path={`${SUBDIRECTORY}/dataview`} element={<DataView role={role} organization={organization} />} />
              <Route path={`${SUBDIRECTORY}/admin`} element={<DistributionManager />} />
              <Route path={`${SUBDIRECTORY}/change-password`} element={this.renderPasswordChange()} />
            </Routes>
          </div>
        </div>
        {/* Custom Divider */}
        <div className="footer-divider"></div>

        {/* Footer with Logos */}
        <div className="footer-logo-container">
          <a href="https://ukneqasmicro.org.uk/" target="_blank" rel="noopener noreferrer">
            <img
              src={`${SUBDIRECTORY}/images/logo1.png`}
              alt="UK NEQAS Microbiology"
              className="footer-logo"
            />
          </a>

          <a href="https://www.cranfield.ac.uk/" target="_blank" rel="noopener noreferrer">
            <img
              src={`${SUBDIRECTORY}/images/logo2.png`}
              alt="Cranfield University"
              className="footer-logo footer-logo2"  // Add a second class for styling
            />
          </a>
        </div>


        {/* Cookie Notice */}
        <CookieNotice />
      </Router>
    );
  }
  /**
   * Main render method.
   * Renders the application or login form based on the user's authentication status
   * and the window width.
   * @returns {JSX.Element} The rendered component.
   */
  render() {
    const { loggedIn, windowWidth, minWidth } = this.state;

    if (windowWidth < minWidth) {
      return (
        <div className="warning-message" style={styles.warning}>
          <h2>Warning</h2>
          <p>Your screen width is too small to use this application. Please increase your browser window width to at least {minWidth}px.</p>
        </div>
      );
    }

    return loggedIn ? this.renderApp() : this.renderLoginForm();
  }
}

// Cookie Notice Component
const CookieNotice = () => {
  return (
    <div style={cookieNoticeStyles.container}>
      <p style={cookieNoticeStyles.text}>
        This site uses only essential cookies to ensure functionality.
      </p>
    </div>
  );
};

const cookieNoticeStyles = {
  container: {
    position: 'fixed',
    bottom: 0,
    left: '50%',
    transform: 'translateX(-50%)',
    width: '100%',
    maxWidth: '100%',
    backgroundColor: '#f8f9fa',
    color: '#333',
    padding: '10px',
    textAlign: 'center',
    borderTop: '1px solid #ccc',
    boxSizing: 'border-box',
    zIndex: 1000,
  },
  text: {
    margin: 0,
    fontSize: '14px',
    fontWeight: '400',
    textAlign: 'center',
  },
};

const styles = {
  warning: {
    textAlign: 'center',
    marginTop: '20%',
    padding: '20px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    border: '1px solid #f5c6cb',
    borderRadius: '5px',
    maxWidth: '400px',
    margin: 'auto',
  },
};

export default App;
