import { useCallback } from 'react';
import { useAuth } from '../hooks/useAuth.jsx';
import { useLanguage } from '../hooks/useLanguage.jsx';
import { getTranslation } from '../utils/translations.js';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';
import InputBar from './InputBar';
import PanicButton from './PanicButton';
import { useChat } from '../hooks/useChat';
import { panicWipe } from '../utils/api';

export default function ChatApp() {
  const { user, logout } = useAuth();
  const { language, setLanguage } = useLanguage();
  const navigate = useNavigate();
  const { messages, sessionId, isLoading, error, agentInfo, send, upload, clearMessages } =
    useChat();

  const t = (key) => getTranslation(key, language);

  // Redirect if not authenticated
  if (!user) {
    navigate('/login');
    return null;
  }

  const handlePanic = useCallback(async () => {
    if (sessionId) {
      try {
        await panicWipe(sessionId);
      } catch {
        // Silently fail — we're leaving anyway
      }
    }
    clearMessages();
  }, [sessionId, clearMessages]);

  const handleQuickAction = useCallback(
    (text) => {
      send(text);
    },
    [send]
  );

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="app-container">
      <Sidebar sessionId={sessionId} agentInfo={agentInfo} onLogout={handleLogout} />

      <main className="chat-area">
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-info">
            <div className="agent-avatar">⚖️</div>
            <div>
              <h2>{t('chat.legal_assistant')}</h2>
              <div className="agent-status">
                {isLoading ? t('chat.thinking') : t('chat.ready_help')}
              </div>
            </div>
          </div>

          <div className="chat-header-actions">
            <select 
              className="lang-selector" 
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              aria-label="Language"
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="ta">தமிழ்</option>
              <option value="bn">বাংলা</option>
            </select>

            <PanicButton onConfirm={handlePanic} />

            <button
              onClick={handleLogout}
              className="btn-logout"
              title="Logout"
            >
              🚪 {t('auth.logout')}
            </button>
          </div>
        </div>

        {/* Messages */}
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onQuickAction={handleQuickAction}
        />

        {/* Error toast */}
        {error && <div className="toast">⚠️ {error}</div>}

        {/* Input */}
        <InputBar
          onSend={send}
          onUpload={upload}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}
