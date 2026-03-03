import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { confirmSignUp, autoSignIn } from 'aws-amplify/auth';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function ConfirmSignupPage() {
  const [confirmationCode, setConfirmationCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const userEmail = sessionStorage.getItem('userEmail') || 'your email';

  const t = (key) => getTranslation(key, language);

  const handleConfirmSignup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await confirmSignUp({
        username: userEmail,
        confirmationCode,
      });

      // Attempt automatic sign-in
      try {
        await autoSignIn();
        navigate('/chat');
      } catch (autoSignInErr) {
        // User needs to sign in manually
        navigate('/login');
      }
    } catch (err) {
      if (err.code === 'CodeMismatchException') {
        setError('Invalid confirmation code. Please check your email and try again.');
      } else if (err.code === 'ExpiredCodeException') {
        setError('Confirmation code has expired. Please sign up again.');
      } else {
        setError(err.message || 'Failed to confirm account');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="language-selector">
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="en">English</option>
          <option value="hi">हिन्दी (Hindi)</option>
          <option value="ta">தமிழ் (Tamil)</option>
          <option value="bn">বাংলা (Bengali)</option>
        </select>
      </div>

      <div className="auth-box">
        {/* Back Button */}
        <Link to="/signup" className="back-button">
          ← Back to Sign Up
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <span className="logo-icon">✉️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Confirmation Form */}
        <form onSubmit={handleConfirmSignup} className="auth-form">
          <h2>Confirm Your Email</h2>
          <p className="auth-subtitle">
            Enter the confirmation code sent to <strong>{userEmail}</strong>
          </p>

          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="code">Confirmation Code</label>
            <input
              id="code"
              type="text"
              value={confirmationCode}
              onChange={(e) => setConfirmationCode(e.target.value.toUpperCase())}
              placeholder="000000"
              required
              disabled={loading}
              maxLength="6"
            />
            <small>Check your email (including spam folder) for the 6-digit code</small>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? 'Verifying...' : 'Confirm Email'}
          </button>
        </form>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            Didn't receive the code? Check your spam folder or sign up again to request a new code.
          </p>
        </div>
      </div>

      {/* Sidebar Info */}
      <div className="auth-sidebar">
        <div className="sidebar-content">
          <h3>Why Confirm Your Email?</h3>
          <ul className="help-list">
            <li>
              <span className="help-icon">🔒</span>
              <div>
                <strong>Secure Account</strong>
                <p>Verifies you own this email address</p>
              </div>
            </li>
            <li>
              <span className="help-icon">📧</span>
              <div>
                <strong>Account Recovery</strong>
                <p>Allows password reset if needed</p>
              </div>
            </li>
            <li>
              <span className="help-icon">🛡️</span>
              <div>
                <strong>Protection</strong>
                <p>Prevents unauthorized access</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
