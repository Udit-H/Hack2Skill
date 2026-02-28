const AGENT_LABELS = {
    orchestrator: 'Triage',
    legal: 'Legal Agent',
    shelter: 'Shelter Agent',
    completed: 'Complete',
};

const STATUS_LABELS = {
    awaiting_docs: 'Awaiting Documents',
    awaiting_user_info: 'Gathering Info',
    awaiting_consent: 'Awaiting Consent',
    ready_to_draft: 'Ready to Draft',
};

function getStatusBadgeClass(status) {
    if (status === 'ready_to_draft') return 'completed';
    if (status === 'awaiting_consent') return 'pending';
    return 'active';
}

export default function Sidebar({ sessionId, agentInfo }) {
    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar-logo">
                <div className="logo-icon">⚖️</div>
                <div>
                    <h1>Sahayak</h1>
                    <span>Last Mile Justice Navigator</span>
                </div>
            </div>

            {/* Privacy */}
            <div className="privacy-indicator">
                <div className="dot"></div>
                <span>Private & Encrypted Session</span>
            </div>

            {/* Session Info */}
            <div className="sidebar-section">
                <div className="sidebar-section-title">Session</div>
                <div className="status-card">
                    <div className="status-card-header">
                        <span className="status-card-label">Session ID</span>
                    </div>
                    <div className="status-card-value" style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                        {sessionId || 'Initializing...'}
                    </div>
                </div>
            </div>

            {/* Agent Status */}
            <div className="sidebar-section">
                <div className="sidebar-section-title">Active Agent</div>
                <div className="status-card">
                    <div className="status-card-header">
                        <span className="status-card-label">
                            {AGENT_LABELS[agentInfo.activeAgent] || agentInfo.activeAgent}
                        </span>
                        <span className={`status-badge ${getStatusBadgeClass(agentInfo.workflowStatus)}`}>
                            {agentInfo.activeAgent === 'completed' ? 'Done' : 'Active'}
                        </span>
                    </div>
                    <div className="status-card-value">
                        {STATUS_LABELS[agentInfo.workflowStatus] || agentInfo.workflowStatus}
                    </div>
                </div>
            </div>

            {/* Workflow Progress */}
            <div className="sidebar-section">
                <div className="sidebar-section-title">Workflow Progress</div>

                {['awaiting_docs', 'awaiting_user_info', 'awaiting_consent', 'ready_to_draft'].map(
                    (step, i) => {
                        const steps = ['awaiting_docs', 'awaiting_user_info', 'awaiting_consent', 'ready_to_draft'];
                        const currentIdx = steps.indexOf(agentInfo.workflowStatus);
                        const isCompleted = i < currentIdx;
                        const isCurrent = i === currentIdx;

                        return (
                            <div
                                key={step}
                                className="status-card"
                                style={{
                                    opacity: isCompleted || isCurrent ? 1 : 0.4,
                                    borderColor: isCurrent
                                        ? 'var(--primary-600)'
                                        : 'var(--border-subtle)',
                                }}
                            >
                                <div className="status-card-header">
                                    <span className="status-card-label">
                                        {isCompleted ? '✅ ' : isCurrent ? '▶ ' : '○ '}
                                        {STATUS_LABELS[step]}
                                    </span>
                                </div>
                            </div>
                        );
                    }
                )}
            </div>

            {/* Help */}
            <div className="sidebar-section" style={{ marginTop: 'auto' }}>
                <div className="status-card" style={{ background: 'rgba(20, 184, 166, 0.06)' }}>
                    <div className="status-card-value" style={{ fontSize: '0.75rem', lineHeight: '1.6' }}>
                        💡 <strong>Tip:</strong> Upload your rent agreement or eviction notice
                        for faster processing. Sahayak can extract details automatically.
                    </div>
                </div>
            </div>
        </aside>
    );
}
