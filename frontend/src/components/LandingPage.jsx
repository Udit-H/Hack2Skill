import { Link } from 'react-router-dom';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import './LandingPage.css';

export default function LandingPage() {
  const { language, setLanguage } = useLanguage();

  const t = (key) => getTranslation(key, language);

  return (
    <div className="landing-container">
      {/* Language Selector in Top Right */}
      <div className="language-selector-top">
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="en">English</option>
          <option value="hi">हिन्दी (Hindi)</option>
          <option value="ta">தமிழ் (Tamil)</option>
          <option value="bn">বাংলা (Bengali)</option>
        </select>
      </div>

      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-content">
          <div className="logo">
            <span className="logo-icon">🏛️</span>
            <span className="logo-text">Sahayak</span>
          </div>
          <div className="nav-links">
            <a href="#features">{t('landing.features')}</a>
            <a href="#about">{t('landing.about')}</a>
            <a href="#contact">{t('landing.contact')}</a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            {t('landing.hero_title')}
            <span className="gradient-text"> {t('landing.hero_subtitle_accent')}</span>
          </h1>
          <p className="hero-subtitle">
            {t('landing.hero_description')}
          </p>

          <div className="hero-cta">
            <Link to="/login" className="btn btn-primary">
              {t('auth.login')}
            </Link>
            <Link to="/signup" className="btn btn-secondary">
              {t('auth.sign_up')}
            </Link>
          </div>

          <div className="hero-image">
            <div className="hero-graphic">
              <div className="graphic-element graphic-1">📋</div>
              <div className="graphic-element graphic-2">🏠</div>
              <div className="graphic-element graphic-3">⚖️</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <h2>{t('landing.how_sahayak_helps')}</h2>
        
        <div className="features-grid">
          {/* Shelter Assistance */}
          <div className="feature-card">
            <div className="feature-icon">🏠</div>
            <h3>{t('landing.shelter_assistance')}</h3>
            <p>
              {t('landing.shelter_description')}
            </p>
            <ul className="feature-list">
              <li>{t('landing.shelter_feature_1')}</li>
              <li>{t('landing.shelter_feature_2')}</li>
              <li>{t('landing.shelter_feature_3')}</li>
            </ul>
          </div>

          {/* Legal Assistance */}
          <div className="feature-card">
            <div className="feature-icon">⚖️</div>
            <h3>{t('landing.legal_support')}</h3>
            <p>
              {t('landing.legal_description')}
            </p>
            <ul className="feature-list">
              <li>{t('landing.legal_feature_1')}</li>
              <li>{t('landing.legal_feature_2')}</li>
              <li>{t('landing.legal_feature_3')}</li>
            </ul>
          </div>

          {/* 24/7 Availability */}
          <div className="feature-card">
            <div className="feature-icon">⏰</div>
            <h3>{t('landing.support_24_7')}</h3>
            <p>
              {t('landing.support_description')}
            </p>
            <ul className="feature-list">
              <li>{t('landing.support_feature_1')}</li>
              <li>{t('landing.support_feature_2')}</li>
              <li>{t('landing.support_feature_3')}</li>
            </ul>
          </div>

          {/* Privacy & Safety */}
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>{t('landing.privacy_safety')}</h3>
            <p>
              {t('landing.privacy_description')}
            </p>
            <ul className="feature-list">
              <li>{t('landing.privacy_feature_1')}</li>
              <li>{t('landing.privacy_feature_2')}</li>
              <li>{t('landing.privacy_feature_3')}</li>
            </ul>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="about-section">
        <div className="about-content">
          <h2>{t('landing.about_sahayak')}</h2>
          <p className="about-text">
            {t('landing.about_description')}
            Sahayak connects you with resources and legal guidance.
          </p>
          
          <div className="about-stats">
            <div className="stat">
              <h4>24/7</h4>
              <p>Always Available</p>
            </div>
            <div className="stat">
              <h4>{t('landing.stat_free')}</h4>
              <p>{t('landing.stat_free_desc')}</p>
            </div>
            <div className="stat">
              <h4>{t('landing.stat_safe')}</h4>
              <p>{t('landing.stat_safe_desc')}</p>
            </div>
            <div className="stat">
              <h4>{t('landing.stat_quick')}</h4>
              <p>{t('landing.stat_quick_desc')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2>{t('landing.ready_help')}</h2>
        <p>{t('landing.join_thousands')}</p>
        <div className="cta-buttons">
          <Link to="/signup" className="btn btn-primary btn-large">
            {t('landing.create_account_now')}
          </Link>
          <Link to="/login" className="btn btn-secondary btn-large">
            {t('landing.already_member')}
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-section">
            <h4>Sahayak</h4>
            <p>Last Mile Justice Navigator</p>
          </div>
          <div className="footer-section">
            <h4>Links</h4>
            <ul>
              <li><a href="#features">Features</a></li>
              <li><a href="#about">About</a></li>
              <li><a href="#contact">Contact</a></li>
            </ul>
          </div>
          <div className="footer-section">
            <h4>Legal</h4>
            <ul>
              <li><a href="/privacy">Privacy</a></li>
              <li><a href="/terms">Terms</a></li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2026 Sahayak. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
