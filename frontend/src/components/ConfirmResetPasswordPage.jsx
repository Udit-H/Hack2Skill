import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { confirmResetPassword } from 'aws-amplify/auth';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function ConfirmResetPasswordPage() {
  const [confirmationCode, setConfirmationCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1); // Step 1: Enter code, Step 2: Enter new password
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const userEmail = sessionStorage.getItem('resetPasswordEmail') || 'your email';

  const t = (key) => getTranslation(key, language);

  const handleConfirmReset = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (step === 1) {
      // Move to step 2 - setting new password
      setStep(2);
      setLoading(false);
      return;
    }

    // Step 2: Confirm reset with code and new password
    if (newPassword !== confirmNewPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    try {
      await confirmResetPassword({
        username: userEmail,
        confirmationCode,
        newPassword,
      });

      setSuccess('Password reset successful! Redirecting to login...');
      sessionStorage.removeItem('resetPasswordEmail');
      sessionStorage.removeItem('awaitingResetCode');
      
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err) {
      if (err.code === 'CodeMismatchException') {
        setError('Invalid confirmation code. Check your email and try again.');
      } else if (err.code === 'ExpiredCodeException') {
        setError('Confirmation code has expired. Request a new password reset.');
      } else if (err.code === 'InvalidPasswordException') {
        setError('Password does not meet complexity requirements.');
      } else {
        setError(err.message || 'Failed to reset password');
      }
      setStep(1); // Go back to step 1
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
        <Link to="/login" className="back-button">
          ← Back to Login
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <span className="logo-icon">🔐</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Reset Password Confirmation Form */}
        <form onSubmit={handleConfirmReset} className="auth-form">
          <h2>Reset Your Password</h2>
          {step === 1 ? (
            <>
              <p className="auth-subtitle">
                Enter the verification code sent to <strong>{userEmail}</strong>
              </p>

              {error && <div className="error-message">{error}</div>}

              <div className="form-group">
                <label htmlFor="code">Verification Code</label>
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
                <small>6-digit code from your email</small>
              </div>

              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? 'Verifying Code...' : 'Next'}
              </button>
            </>
          ) : (
            <>
              <p className="auth-subtitle">
                Enter your new password
              </p>

              {error && <div className="error-message">{error}</div>}
              {success && <div className="success-message">{success}</div>}

              <div className="form-group">
                <label htmlFor="newPassword">New Password</label>
                <input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
                <small>At least 12 characters with uppercase, lowercase, number, and special character (e.g., !@#$%^&*)</small>
              </div>

              <div className="form-group">
                <label htmlFor="confirmNewPassword">Confirm Password</label>
                <input
                  id="confirmNewPassword"
                  type="password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
              </div>

              <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                {loading ? 'Resetting Password...' : 'Reset Password'}
              </button>
            </>
          )}
        </form>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            {step === 1
              ? "Didn't receive the code? Check spam folder or request a new reset."
              : "Use a strong password you haven't used on this site before."}
          </p>
        </div>
      </div>

      {/* Sidebar Info */}
      <div className="auth-sidebar">
        <div className="sidebar-content">
          <h3>Security Tips</h3>
          <ul className="help-list">
            <li>
              <span className="help-icon">🔒</span>
              <div>
                <strong>Strong Password</strong>
                <p>Use unique passwords for each account</p>
              </div>
            </li>
            <li>
              <span className="help-icon">📧</span>
              <div>
                <strong>Secure Email</strong>
                <p>Protect your email account too</p>
              </div>
            </li>
            <li>
              <span className="help-icon">💾</span>
              <div>
                <strong>Password Manager</strong>
                <p>Consider using one to generate strong passwords</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
