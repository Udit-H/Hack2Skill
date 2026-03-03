import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { signUp, confirmSignUp, autoSignIn } from 'aws-amplify/auth';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './AuthPages.css';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();

  const t = (key) => getTranslation(key, language);

  const validateForm = () => {
    if (!email || !password || !confirmPassword) {
      setError(t('auth.all_fields_required'));
      return false;
    }
    if (password.length < 12) {
      setError('Password must be at least 12 characters long.');
      return false;
    }
    if (password !== confirmPassword) {
      setError(t('auth.password_mismatch'));
      return false;
    }
    return true;
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) return;

    setLoading(true);

    try {
      // Step 1: Sign up user in Cognito User Pool
      const { userId } = await signUp({
        username: email,
        password,
        userAttributes: {
          email,
        },
      });

      // Step 2: Confirm user (Cognito will send verification code to email)
      // The app should navigate to a confirmation page asking for the code
      // For now, we'll try auto-sign-in if configured
      try {
        await autoSignIn();
        navigate('/chat');
      } catch (autoSignInErr) {
        // If auto sign-in fails, user needs to confirm email first
        // Store userId in sessionStorage for the confirmation page
        sessionStorage.setItem('waitingForEmailConfirmation', 'true');
        sessionStorage.setItem('userEmail', email);
        navigate('/confirm-signup');
      }
    } catch (err) {
      // Map Cognito errors to user-friendly messages
      if (err.code === 'UsernameExistsException') {
        setError('An account with this email already exists.');
      } else if (err.code === 'InvalidPasswordException') {
        setError('Password must be at least 12 characters with uppercase, lowercase, number, and special character (e.g., !@#$%^&*).');
      } else {
        setError(err.message || 'Failed to create account');
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
        <Link to="/" className="back-button">
          {t('auth.back_to_home')}
        </Link>

        {/* Logo */}
        <div className="auth-logo">
          <span className="logo-icon">🏛️</span>
          <h1>Sahayak</h1>
          <p>Last Mile Justice Navigator</p>
        </div>

        {/* Signup Form */}
        <form onSubmit={handleSignup} className="auth-form">
          <h2>{t('auth.create_account')}</h2>
          <p className="auth-subtitle">{t('auth.signup_desc')}</p>

          {error && <div className="error-message">{error}</div>}

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

          <div className="form-group">
            <label htmlFor="password">{t('auth.password')}</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
            <small>At least 12 characters: uppercase, lowercase, number, special character (!@#$%^&*)</small>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">{t('auth.confirm_password')}</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          <div className="terms-checkbox">
            <input type="checkbox" id="terms" required disabled={loading} />
            <label htmlFor="terms">
              {t('auth.by_continuing')} <a href="/terms" target="_blank" rel="noopener noreferrer">{t('auth.terms_of_service')}</a> {t('auth.and')}{' '}
              <a href="/privacy" target="_blank" rel="noopener noreferrer">{t('auth.privacy_policy')}</a>
            </label>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? t('auth.sending_email') : t('auth.create_account_btn')}
          </button>
        </form>

        {/* Login Link */}
        <p className="auth-switch">
          {t('auth.already_have_account')}{' '}
          <Link to="/login" className="auth-link">
            {t('auth.sign_in_here')}
          </Link>
        </p>

        {/* Help Text */}
        <div className="auth-help">
          <p>
            Your information is secure and will never be shared without your consent.
          </p>
        </div>
      </div>

      {/* Sidebar Info */}
      <div className="auth-sidebar">
        <div className="sidebar-content">
          <h3>Why Join Sahayak?</h3>
          <ul className="help-list">
            <li>
              <span className="help-icon">⚡</span>
              <div>
                <strong>Instant Access</strong>
                <p>Get help immediately upon signup</p>
              </div>
            </li>
            <li>
              <span className="help-icon">🔒</span>
              <div>
                <strong>Completely Private</strong>
                <p>Your crisis stays between you and us</p>
              </div>
            </li>
            <li>
              <span className="help-icon">🌍</span>
              <div>
                <strong>24/7 Available</strong>
                <p>Support whenever you need it most</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
