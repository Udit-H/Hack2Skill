import { useState } from 'react';

export default function PanicButton({ onConfirm }) {
    const [showModal, setShowModal] = useState(false);

    const handleConfirm = () => {
        setShowModal(false);
        onConfirm();
        // Redirect to a benign page after a brief delay
        setTimeout(() => {
            window.location.href = 'https://www.google.com';
        }, 300);
    };

    return (
        <>
            <button
                className="panic-button"
                onClick={() => setShowModal(true)}
                title="Emergency: Wipe all data and leave"
                aria-label="Emergency exit"
            >
                <span className="icon">🛑</span>
                Exit Now
            </button>

            {showModal && (
                <div className="panic-overlay" onClick={() => setShowModal(false)}>
                    <div className="panic-modal" onClick={(e) => e.stopPropagation()}>
                        <h3>🛑 Emergency Exit</h3>
                        <p>
                            This will <strong>permanently delete</strong> all your chat history
                            and session data, then redirect you to Google. This cannot be undone.
                        </p>
                        <div className="panic-modal-actions">
                            <button
                                className="panic-confirm-btn cancel"
                                onClick={() => setShowModal(false)}
                            >
                                Go Back
                            </button>
                            <button
                                className="panic-confirm-btn danger"
                                onClick={handleConfirm}
                            >
                                Wipe & Exit
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
