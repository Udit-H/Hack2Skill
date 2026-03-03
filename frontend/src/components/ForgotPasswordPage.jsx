import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { resetPassword, confirmResetPassword } from 'aws-amplify/auth';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const t = (key) => getTranslation(key, language);

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      // Initiate password reset flow - Cognito sends code to email
      await resetPassword({ username: email });
      setSuccess(t('auth.reset_email_sent'));
      // Store email for confirmation step
      sessionStorage.setItem('resetPasswordEmail', email);
      sessionStorage.setItem('awaitingResetCode', 'true');
      setEmail('');
      setTimeout(() => {
        navigate('/confirm-reset-password');
      }, 2000);
    } catch (err) {
      if (err.code === 'UserNotFoundException') {
        setError('No account found with this email.');
      } else {
        setError(err.message || 'Failed to send reset email');
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
        <Link to="/login" className="back-button">
          ← Back to Login
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <span className="logo-icon">🔐</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Reset Password Form */}
        <form onSubmit={handleResetPassword} className="auth-form">
          <h2>{t('auth.reset_password')}</h2>
          <p className="auth-subtitle">{t('auth.reset_desc')}</p>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          <div className="form-group">
            <label htmlFor="email">{t('auth.email')}</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? t('auth.sending_email') : t('auth.send_reset_email_btn')}
          </button>
        </form>

        {/* Back to Login Link */}
        <p className="auth-switch">
          Remember your password?{' '}
          <Link to="/login" className="auth-link">
            Sign in here
          </Link>
        </p>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            Check your email (including spam folder) for the password reset link.
            Click the link to create a new password.
          </p>
        </div>
      </div>
    </div>
  );
}
