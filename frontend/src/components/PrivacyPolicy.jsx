import { Link } from 'react-router-dom';
import './LegalPages.css';

export default function PrivacyPolicy() {
  return (
    <div className="legal-page">
      <div className="legal-content">
        <Link to="/" className="back-link">← Back to Home</Link>
        
        <h1>Privacy Policy</h1>
        <p className="last-updated">Last Updated: February 28, 2026</p>

        <section>
          <h2>1. Introduction</h2>
          <p>
            Sahayak ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your personal information when you use our crisis support services.
          </p>
        </section>

        <section>
          <h2>2. Information We Collect</h2>
          <h3>Account Information</h3>
          <ul>
            <li>Email address</li>
            <li>Authentication credentials</li>
            <li>Profile information you provide</li>
          </ul>

          <h3>Crisis Support Data</h3>
          <ul>
            <li>Messages and communications with our AI assistant</li>
            <li>Location information (for shelter recommendations)</li>
            <li>Documents you upload (for legal assistance)</li>
            <li>Session metadata and timestamps</li>
          </ul>

          <h3>Technical Information</h3>
          <ul>
            <li>Device type and browser information</li>
            <li>IP address</li>
            <li>Usage analytics and performance data</li>
          </ul>
        </section>

        <section>
          <h2>3. How We Use Your Information</h2>
          <p>We use your information to:</p>
          <ul>
            <li>Provide emergency legal and shelter assistance</li>
            <li>Match you with appropriate resources</li>
            <li>Improve our AI assistance capabilities</li>
            <li>Ensure platform security and prevent abuse</li>
            <li>Communicate important updates or safety information</li>
          </ul>
        </section>

        <section>
          <h2>4. Data Security</h2>
          <p>
            We implement industry-standard security measures to protect your data:
          </p>
          <ul>
            <li>End-to-end encryption for sensitive communications</li>
            <li>Secure Amazon Cognito authentication</li>
            <li>Regular security audits</li>
            <li>Limited employee access to user data</li>
          </ul>
        </section>

        <section>
          <h2>5. Data Sharing</h2>
          <p>
            <strong>We do NOT sell your personal information.</strong>
          </p>
          <p>We may share data only in these circumstances:</p>
          <ul>
            <li><strong>With your consent:</strong> When you authorize us to share with shelters or legal services</li>
            <li><strong>Emergency situations:</strong> If required to prevent imminent harm</li>
            <li><strong>Legal obligations:</strong> When required by law or court order</li>
            <li><strong>Service providers:</strong> With trusted partners who help operate our service (under strict confidentiality agreements)</li>
          </ul>
        </section>

        <section>
          <h2>6. Your Rights</h2>
          <p>You have the right to:</p>
          <ul>
            <li><strong>Access:</strong> Request a copy of your personal data</li>
            <li><strong>Correction:</strong> Update or correct your information</li>
            <li><strong>Deletion:</strong> Request deletion of your account and data</li>
            <li><strong>Export:</strong> Download your data in a portable format</li>
            <li><strong>Opt-out:</strong> Unsubscribe from non-essential communications</li>
          </ul>
        </section>

        <section>
          <h2>7. Data Retention</h2>
          <p>
            We retain your data only as long as necessary to provide services or as required by law. You can request immediate deletion of your data at any time using the "Panic Button" feature or by contacting us.
          </p>
        </section>

        <section>
          <h2>8. Changes to Privacy Policy</h2>
          <p>
            We may update this Privacy Policy periodically. We will notify you of significant changes via email or in-app notification. Your continued use after changes constitutes acceptance.
          </p>
        </section>

        <section className="emphasis">
          <h2>Your Safety is Our Priority</h2>
          <p>
            We understand that users of Sahayak may be in vulnerable situations. Your privacy and safety are paramount. All team members are trained in trauma-informed practices and data handling.
          </p>
        </section>
      </div>
    </div>
  );
}
