export default function MessageBubble({ message }) {
    const isUser = message.role === 'user';
    const time = new Date(message.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
    });

    return (
        <div className={`message ${isUser ? 'user' : 'assistant'}`}>
            <div className="message-avatar">
                {isUser ? '👤' : '⚖️'}
            </div>
            <div>
                <div className="message-bubble">
                    {message.content}
                </div>
                <div className="message-time">{time}</div>
            </div>
        </div>
    );
}
