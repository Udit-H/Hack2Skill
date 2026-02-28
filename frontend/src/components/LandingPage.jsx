import { Link } from 'react-router-dom';
import './LandingPage.css';

export default function LandingPage() {
  return (
    <div className="landing-container">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-content">
          <div className="logo">
            <span className="logo-icon">🏛️</span>
            <span className="logo-text">Sahayak</span>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#about">About</a>
            <a href="#contact">Contact</a>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">
            Justice for All
            <span className="gradient-text"> Last Mile</span>
          </h1>
          <p className="hero-subtitle">
            Emergency legal assistance and shelter support when you need it most.
            Trauma-informed guidance through your crisis.
          </p>

          <div className="hero-cta">
            <Link to="/login" className="btn btn-primary">
              Login
            </Link>
            <Link to="/signup" className="btn btn-secondary">
              Sign Up
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
        <h2>How Sahayak Helps You</h2>
        
        <div className="features-grid">
          {/* Shelter Assistance */}
          <div className="feature-card">
            <div className="feature-icon">🏠</div>
            <h3>Emergency Shelter</h3>
            <p>
              Find safe, verified shelters near you instantly. Get immediate assistance
              if you're facing homelessness or unsafe living conditions.
            </p>
            <ul className="feature-list">
              <li>Real-time shelter availability</li>
              <li>Trauma-informed support</li>
              <li>SMS notifications to managers</li>
            </ul>
          </div>

          {/* Legal Assistance */}
          <div className="feature-card">
            <div className="feature-icon">⚖️</div>
            <h3>Legal Support</h3>
            <p>
              Access affordable legal help for property disputes, evictions, and other
              civil matters. Document processing made simple.
            </p>
            <ul className="feature-list">
              <li>AI-powered document analysis</li>
              <li>Legal form generation</li>
              <li>Expert guidance</li>
            </ul>
          </div>

          {/* 24/7 Availability */}
          <div className="feature-card">
            <div className="feature-icon">⏰</div>
            <h3>24/7 Support</h3>
            <p>
              Crisis doesn't follow business hours. Our AI assistant is available
              anytime to help you navigate your situation.
            </p>
            <ul className="feature-list">
              <li>Always available</li>
              <li>Instant responses</li>
              <li>Multi-language support</li>
            </ul>
          </div>

          {/* Privacy & Safety */}
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Privacy & Safety</h3>
            <p>
              Your data and identity are protected. We never share your information
              without consent.
            </p>
            <ul className="feature-list">
              <li>End-to-end encryption</li>
              <li>GDPR compliant</li>
              <li>Anonymous options</li>
            </ul>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="about-section">
        <div className="about-content">
          <h2>About Sahayak</h2>
          <p className="about-text">
            Sahayak is an AI-powered crisis management platform designed to provide
            immediate, trauma-informed assistance to vulnerable populations. Whether
            you're facing homelessness, legal disputes, or need emergency shelter,
            Sahayak connects you with resources and legal guidance.
          </p>
          
          <div className="about-stats">
            <div className="stat">
              <h4>24/7</h4>
              <p>Always Available</p>
            </div>
            <div className="stat">
              <h4>Free</h4>
              <p>No Cost</p>
            </div>
            <div className="stat">
              <h4>Safe</h4>
              <p>Verified Resources</p>
            </div>
            <div className="stat">
              <h4>Quick</h4>
              <p>Instant Help</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <h2>Ready to Get Help?</h2>
        <p>Join thousands who have found assistance through Sahayak.</p>
        <div className="cta-buttons">
          <Link to="/signup" className="btn btn-primary btn-large">
            Create Account Now
          </Link>
          <Link to="/login" className="btn btn-secondary btn-large">
            Already a Member? Login
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
