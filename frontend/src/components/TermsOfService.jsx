import { Link } from 'react-router-dom';
import './LegalPages.css';

export default function TermsOfService() {
  return (
    <div className="legal-page">
      <div className="legal-content">
        <Link to="/" className="back-link">← Back to Home</Link>
        
        <h1>Terms of Service</h1>
        <p className="last-updated">Last Updated: February 28, 2026</p>

        <section>
          <h2>1. Acceptance of Terms</h2>
          <p>
            By accessing and using Sahayak ("the Service"), you accept and agree to be bound by the terms and provision of this agreement.
          </p>
        </section>

        <section>
          <h2>2. Use of Service</h2>
          <p>
            Sahayak provides emergency legal assistance and shelter support. This service is intended for crisis situations and should not replace professional legal counsel or emergency services.
          </p>
          <p>
            You agree to:
          </p>
          <ul>
            <li>Provide accurate information</li>
            <li>Use the service lawfully and ethically</li>
            <li>Not misuse or attempt to harm the platform</li>
            <li>Respect other users' privacy and rights</li>
          </ul>
        </section>

        <section>
          <h2>3. Privacy & Data</h2>
          <p>
            We are committed to protecting your privacy. All data is handled according to our Privacy Policy. Your crisis information is kept confidential and secure.
          </p>
        </section>

        <section>
          <h2>4. Emergency Situations</h2>
          <p>
            <strong>Important:</strong> If you are in immediate danger, please contact emergency services (911 or local emergency number) directly. Sahayak is a support tool but does not replace emergency response services.
          </p>
        </section>

        <section>
          <h2>5. Disclaimer</h2>
          <p>
            The information and assistance provided through Sahayak are for informational purposes only and do not constitute legal advice. We recommend consulting with qualified legal professionals for specific legal matters.
          </p>
        </section>

        <section>
          <h2>6. Limitation of Liability</h2>
          <p>
            Sahayak and its operators shall not be liable for any damages arising from the use or inability to use the service, including but not limited to direct, indirect, incidental, or consequential damages.
          </p>
        </section>

        <section>
          <h2>7. Changes to Terms</h2>
          <p>
            We reserve the right to modify these terms at any time. Users will be notified of significant changes. Continued use of the service after changes constitutes acceptance of the modified terms.
          </p>
        </section>

        <section>
          <h2>8. Contact</h2>
          <p>
            For questions about these Terms of Service, please contact us at support@sahayak.example.com
          </p>
        </section>
      </div>
    </div>
  );
}
