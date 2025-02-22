/**
 * @module Toolbar
 * @memberof App
 * @description Renders the application toolbar including navigation links, notification bell, and logout button. Has the tough task of handling the only WebSocket in the application.
 * @returns {JSX.Element} The rendered toolbar.
 */
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUpload, faInfoCircle, faCog, faUser, faSignOutAlt, faBell, faTimes } from '@fortawesome/free-solid-svg-icons';
import { io } from "socket.io-client";

const Toolbar = ({ role, email, handleLogout }) => {
  const [activeLink, setActiveLink] = useState(`/`); // Default active link
  const [notifications, setNotifications] = useState([]); // Store notifications
  const [dismissedNotifications, setDismissedNotifications] = useState([]); // Store notifications
  const [hasNewNotifications, setHasNewNotifications] = useState(false); // Twinkle effect
  const [socketInstance, setSocketInstance] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false); // Show/hide dropdown

   /**
   * Formats a date string into a human-readable format.
   * @param {string} dateString - The date string to format.
   * @returns {string} The formatted date.
   */
  const formatDate = (dateString) => {
    if (!dateString) return "Unknown Date";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  /**
   * Updates the active navigation link.
   * @param {string} path - The path of the clicked link.
   * @returns {void}
   */
  const handleLinkClick = (path) => {
    setActiveLink(path);
  };
  /**
   * Fetches notifications for the current user from the API.
   * @async
   * @returns {Promise<void>}
   */
  const fetchNotifications = async (email) => {
    try {
      if (!email) {
        console.error("Email is required to fetch notifications.");
        return;
      }
  
      const response = await fetch("api/notifications", {
        method: "GET",
        credentials: "include",
      });
  
      if (!response.ok) {
        throw new Error(`Failed to fetch notifications: ${response.statusText}`);
      }
  
      const data = await response.json();
  
      // Sort both dismissed and undismissed notifications by created_at date (descending order)
      const sortedUndismissed = [...(data.undismissed || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      const sortedDismissed = [...(data.dismissed || [])].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
      setDismissedNotifications(sortedDismissed);
      setNotifications(sortedUndismissed);
    } catch (error) {
      console.error("Error fetching notifications:", error);
    }
  };
  

  useEffect(() => {
    // Fetch undismissed notifications from the backend
    fetchNotifications(email);


    // Establish socket connection
    const SUBDIRECTORY=process.env.REACT_APP_SUBDIRECTORY_NAME || ""
    const socket = io("/", {  // Connect to the same host
      path:`${SUBDIRECTORY}/socket.io`,
      transports: ["websocket", "polling"],
      query: { role: role, email: email },
    });

    setSocketInstance(socket);

    socket.on("connect", () => {
      console.log("Connected to server");
      socket.emit("start_redis_listener");
    });

    socket.on("my response", (data) => {
      console.log("Received:", data);
    
      if (data && data.message) {
        setNotifications((prevNotifications) => {
          const isDuplicate = prevNotifications.some(
            (notification) => notification.message === data.message
          );
    
          if (!isDuplicate) {
            setHasNewNotifications(true);
            const updatedNotifications = [
              ...prevNotifications,
              { id: data.id, message: data.message, created_at: data.created_at }
            ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); // Sort after adding new notification
    
            return updatedNotifications;
          }
    
          return prevNotifications;
        });
      }
    });
    

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    // Cleanup: Disconnect the socket when the component unmounts
    return () => {
      socket.disconnect();
    };
  }, [role]);

  /**
   * Dismisses a notification by sending a POST request to the API.
   * Updates notifications and dismissed notifications state.
   * @async
   * @param {number|string} id - The ID of the notification to dismiss.
   * @param {number} index - The index of the notification in the current array.
   * @returns {Promise<void>}
   */
  const toggleDropdown = () => {
    setShowDropdown(!showDropdown);
    setHasNewNotifications(false); // Clear the twinkle effect when dropdown is opened
  };

  /**
   * Dismisses a notification by sending a POST request to the API.
   * Updates notifications and dismissed notifications state.
   * @async
   * @param {number|string} id - The ID of the notification to dismiss.
   * @param {number} index - The index of the notification in the current array.
   * @returns {Promise<void>}
   */
  const dismissNotification = async (id, index) => {
    try {
      const response = await fetch("api/notifications/dismiss", {
        method: "POST",
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        credentials: 'include',
        body: new URLSearchParams({ id }),
      });
  
      if (!response.ok) throw new Error('Failed to dismiss notification');
  
      setNotifications((prev) => {
        const updatedNotifications = prev.filter((_, i) => i !== index);
        return updatedNotifications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); // Sort after removal
      });
  
      setDismissedNotifications((prev) => {
        const updatedDismissed = [...prev, notifications[index]];
        return updatedDismissed.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); // Sort after adding
      });
  
    } catch (error) {
      console.error("Error dismissing notification:", error);
    }
  };
  
  const SUBDIRECTORY=process.env.REACT_APP_SUBDIRECTORY_NAME || ""
  
  return (
    <div className="toolbar">
      <Link to={`${SUBDIRECTORY}/`} className="toolbar-title toolbar-link" onClick={() => handleLinkClick(`${SUBDIRECTORY}/`)}>
        RSV EQA Dashboard
      </Link>
      <div className="toolbar-links">
        <Link
          to={`${SUBDIRECTORY}/upload`}
          className={`toolbar-link ${activeLink === `${SUBDIRECTORY}/upload` ? 'active' : ''}`}
          onClick={() => handleLinkClick(`${SUBDIRECTORY}/upload` )}
        >
          <FontAwesomeIcon icon={faUpload} className="icon" />
          Upload
        </Link>
        <Link
          to={`${SUBDIRECTORY}/about`}
          className={`toolbar-link ${activeLink === `${SUBDIRECTORY}/about`  ? 'active' : ''}`}
          onClick={() => handleLinkClick(`${SUBDIRECTORY}/about` )}
        >
          <FontAwesomeIcon icon={faInfoCircle} className="icon" />
          About
        </Link>
        <Link
          to={`${SUBDIRECTORY}/settings`}
          className={`toolbar-link ${activeLink === `${SUBDIRECTORY}/settings`  ? 'active' : ''}`}
          onClick={() => handleLinkClick(`${SUBDIRECTORY}/setting` )}
        >
          <FontAwesomeIcon icon={faCog} className="icon" />
          Settings
        </Link>
        {role === 'superuser' && (
          <Link
            to={`${SUBDIRECTORY}/admin`}
            className={`toolbar-link ${activeLink === `${SUBDIRECTORY}/admin`  ? 'active' : ''}`}
            onClick={() => handleLinkClick(`${SUBDIRECTORY}/admin`)}
          >
            <FontAwesomeIcon icon={faUser} className="icon" />
            Admin
          </Link>
        )}

        {/* Notification Bell */}
        <div className="notification-container">
          <button className="notification-button" onClick={toggleDropdown}>
            <FontAwesomeIcon icon={faBell} className={`icon ${hasNewNotifications ? 'twinkle' : ''}`} />
            {notifications.length > 0 && <span className="notification-count">{notifications.length}</span>}
          </button>
          {showDropdown && (
            <div className="notification-dropdown">
              {notifications.length > 0 ? (
                <>
                  {notifications.map((notification, index) => (
                    <div key={index} className="notification-item">
                      <span className="notification-message">{notification.message}</span>
                      <span className="notification-date">{formatDate(notification.created_at)}</span>
                      <button className="dismiss-button" onClick={() => dismissNotification(notification.id, index)}>
                        <FontAwesomeIcon icon={faTimes} />
                      </button>
                    </div>
                  ))}
                </>
              ) : (
                <div></div>
              )}

              {/* Dismissed notifications */}
              {dismissedNotifications.length > 0 && (
                <>
                  {dismissedNotifications.map((notification, index) => (
                    <div key={index} className="notification-item dismissed">
                      <span className="notification-message">{notification.message}</span>
                      <span className="notification-date">{formatDate(notification.created_at)}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>

        <button onClick={handleLogout} className="toolbar-logout-button">
          <FontAwesomeIcon icon={faSignOutAlt} className="icon" />
          Logout
        </button>
      </div>
    </div>
  );
};

export default Toolbar;
