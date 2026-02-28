import { useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';

export default function ChatWindow({ messages, isLoading, onQuickAction }) {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    if (messages.length === 0 && !isLoading) {
        return (
            <div className="messages-container">
                <div className="welcome-container">
                    <div className="welcome-icon">⚖️</div>
                    <h2>Sahayak</h2>
                    <p>
                        I'm here to help you navigate your situation. Tell me what happened,
                        and I'll guide you through the legal steps — one at a time. Everything
                        stays private on your device.
                    </p>
                    <div className="quick-actions">
                        <button
                            className="quick-action-btn"
                            onClick={() => onQuickAction('I have been unlawfully evicted from my house')}
                        >
                            🏠 I've been evicted
                        </button>
                        <button
                            className="quick-action-btn"
                            onClick={() => onQuickAction('My landlord locked me out and I have nowhere to go')}
                        >
                            🔒 Locked out
                        </button>
                        <button
                            className="quick-action-btn"
                            onClick={() => onQuickAction('I received an eviction notice')}
                        >
                            📄 Got a notice
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="messages-container">
            {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
            ))}

            {isLoading && (
                <div className="typing-indicator">
                    <div className="message-avatar" style={{
                        background: 'linear-gradient(135deg, var(--primary-600), var(--primary-800))',
                        width: 32,
                        height: 32,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.85rem',
                    }}>
                        ⚖️
                    </div>
                    <div className="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            )}

            <div ref={bottomRef} />
        </div>
    );
}
