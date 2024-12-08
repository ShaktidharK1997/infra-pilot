import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { AuthProvider } from "react-oidc-context";

const cognitoAuthConfig = {
  authority: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_pk76Jhr5v",
  client_id: "4jk1ku62b3i9veegqirlptjusf",
  redirect_uri: "https://infrapilot-fe.s3-website-us-east-1.amazonaws.com",
  post_logout_redirect_uri: "https://infrapilot-fe.s3-website-us-east-1.amazonaws.com",
  response_type: "code",
  scope: "email openid phone"

};
const root = ReactDOM.createRoot(document.getElementById("root"));

// wrap the application with AuthProvider
root.render(
  <React.StrictMode>
    <AuthProvider {...cognitoAuthConfig}>
      <App />
    </AuthProvider>
  </React.StrictMode>
);