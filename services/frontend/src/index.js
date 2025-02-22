/**
 * @module SamplePlot
 * 
 * @description Entry point for the React application. Renders the App component within React.StrictMode into the DOM element with id "root". Also calls reportWebVitals for performance measurement.
 *
 * @module index
 */

import React from 'react';
import './App.css';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
