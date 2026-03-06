import { Amplify } from 'aws-amplify';

// Only configure Cognito if credentials are available
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;

let cognitoConfig = null;

if (userPoolId && clientId) {
  cognitoConfig = {
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId: clientId,
        region: import.meta.env.VITE_COGNITO_REGION || 'us-east-1',
        loginWith: {
          email: true,
          username: false,
        },
      },
    },
  };
  
  Amplify.configure(cognitoConfig);
  console.log('✅ Cognito configured');
} else {
  console.warn('⚠️  Cognito credentials not found. Running in anonymous mode only.');
}

export default cognitoConfig;