import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './utils/cognito' // Configure Amplify before anything else
import App from './App.jsx'

document.title = 'Sahayak — Legal Justice Navigator';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
