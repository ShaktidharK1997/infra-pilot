import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { AuthProvider } from "react-oidc-context";
import { WebStorageStateStore } from "oidc-client-ts";
import React, { useEffect } from 'react';
import { useAuth } from "react-oidc-context";


const cognitoAuthConfig = {
  authority: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_pk76Jhr5v",
  client_id: "4jk1ku62b3i9veegqirlptjusf",
  redirect_uri: window.origin,
  post_logout_redirect_uri: window.origin,
  response_type: "code",
  scope: "email openid phone",

  // Add custom state validation
  validateCallbackParams: (params) => {
    // Build the key that react-oidc-context uses for localStorage
    const userDataKey = `oidc.user:https://cognito-idp.us-east-1.amazonaws.com/us-east-1_pk76Jhr5v:4jk1ku62b3i9veegqirlptjusf`;
    
    // Check if we have user data
    const userData = localStorage.getItem(userDataKey);
    
    if (userData) {
      try {
        const parsedData = JSON.parse(userData);
        
        // Check if tokens are still valid
        if (parsedData.expires_at && parsedData.expires_at > Date.now() / 1000) {
          console.log('Valid tokens found, bypassing state validation');
          return true;
        }
      } catch (e) {
        console.error('Error parsing user data:', e);
      }
    }
    
    // If no valid tokens, do normal state validation
    console.log('No valid tokens, performing state validation');
    return params.state && params.code;
  },

  // Add cleanup after successful login
  onSigninCallback: () => {
    // Remove state from URL after successful login
    window.history.replaceState({}, document.title, window.location.pathname);
  }
};

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <AuthProvider {...cognitoAuthConfig}>
      <App />
    </AuthProvider>
  </React.StrictMode>
);