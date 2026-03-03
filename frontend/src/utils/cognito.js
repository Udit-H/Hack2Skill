import { Amplify } from 'aws-amplify';

const cognitoConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      region: import.meta.env.VITE_COGNITO_REGION || 'us-east-1',
      loginWith: {
        email: true,
        username: false,
      },
    },
  },
};

Amplify.configure(cognitoConfig);

export default cognitoConfig;