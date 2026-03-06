import { useState, useEffect } from 'react';
import { listUserSessions } from '../utils/api';

export default function SessionList({ userId, currentSessionId, onSelectSession, onNewChat }) {
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        if (userId && isOpen) {
            loadSessions();
        }
    }, [userId, isOpen]);

    const loadSessions = async () => {
        if (!userId) {
            console.error('❌ No userId available for session list');
            setIsLoading(false);
            return;
        }
        
        try {
            console.log('📡 Loading sessions for user:', userId);
            setIsLoading(true);
            const data = await listUserSessions(userId);
            console.log('✅ Sessions loaded:', data.sessions);
            setSessions(data.sessions || []);
        } catch (err) {
            console.error('❌ Failed to load sessions:', err);
            setSessions([]);
        } finally {
            setIsLoading(false);
        }
    };

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    };

    return (
        <>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="session-list-toggle"
                title="View all chats"
            >
                💬 Chats {sessions.length > 0 ? `(${sessions.length})` : ''}
            </button>

            {isOpen && (
                <div className="session-list-overlay" onClick={() => setIsOpen(false)}>
                    <div className="session-list-panel" onClick={(e) => e.stopPropagation()}>
                        <div className="session-list-header">
                            <h3>Your Conversations</h3>
                            <button
                                onClick={() => setIsOpen(false)}
                                className="session-list-close"
                            >
                                ✕
                            </button>
                        </div>

                        <button
                            onClick={() => {
                                onNewChat();
                                setIsOpen(false);
                            }}
                            className="btn-new-chat"
                        >
                            ➕ New Chat
                        </button>

                        <div className="session-list-content">
                            {!userId ? (
                                <div className="session-list-empty">
                                    ⚠️ User authentication required to view saved chats
                                </div>
                            ) : isLoading ? (
                                <div className="session-list-loading">
                                    <div className="spinner"></div>
                                    Loading your conversations...
                                </div>
                            ) : sessions.length === 0 ? (
                                <div className="session-list-empty">
                                    <div style={{ fontSize: '2rem', marginBottom: 'var(--space-4)' }}>💬</div>
                                    <div style={{ fontWeight: 500, marginBottom: 'var(--space-2)' }}>No conversations yet</div>
                                    <div style={{ fontSize: 'var(--font-size-xs)', opacity: 0.7 }}>
                                        Start a new chat and it will appear here
                                    </div>
                                </div>
                            ) : (
                                sessions.map((session) => (
                                    <div
                                        key={session.session_id}
                                        className={`session-item ${
                                            session.session_id === currentSessionId
                                                ? 'active'
                                                : ''
                                        }`}
                                        onClick={() => {
                                            if (session.session_id !== currentSessionId) {
                                                onSelectSession(session.session_id);
                                                setIsOpen(false);
                                            }
                                        }}
                                    >
                                        <div className="session-item-preview">
                                            {session.last_message}
                                        </div>
                                        <div className="session-item-meta">
                                            <span className="session-item-time">
                                                {formatTimestamp(session.last_timestamp)}
                                            </span>
                                            <span className="session-item-count">
                                                {session.message_count} messages
                                            </span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
