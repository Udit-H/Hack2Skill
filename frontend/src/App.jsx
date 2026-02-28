import { useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import InputBar from './components/InputBar';
import PanicButton from './components/PanicButton';
import { useChat } from './hooks/useChat';
import { panicWipe } from './utils/api';

export default function App() {
  const { messages, sessionId, isLoading, error, agentInfo, send, upload, clearMessages } =
    useChat();

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

  return (
    <div className="app-container">
      <Sidebar sessionId={sessionId} agentInfo={agentInfo} />

      <main className="chat-area">
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-info">
            <div className="agent-avatar">⚖️</div>
            <div>
              <h2>Sahayak Legal Assistant</h2>
              <div className="agent-status">
                {isLoading ? 'Thinking...' : 'Ready to help'}
              </div>
            </div>
          </div>

          <div className="chat-header-actions">
            <select className="lang-selector" defaultValue="en" aria-label="Language">
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="ta">தமிழ்</option>
              <option value="bn">বাংলা</option>
            </select>

            <PanicButton onConfirm={handlePanic} />
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
