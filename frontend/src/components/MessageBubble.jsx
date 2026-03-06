import { Fragment } from 'react';

function renderMessageContent(content) {
    const input = String(content ?? '');
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const nodes = [];
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(input)) !== null) {
        const [fullMatch, linkText, linkHref] = match;
        const start = match.index;

        if (start > lastIndex) {
            nodes.push(input.slice(lastIndex, start));
        }

        nodes.push(
            <a
                key={`${linkHref}-${start}`}
                href={linkHref}
                download
                target="_blank"
                rel="noopener noreferrer"
            >
                {linkText}
            </a>
        );

        lastIndex = start + fullMatch.length;
    }

    if (lastIndex < input.length) {
        nodes.push(input.slice(lastIndex));
    }

    return nodes.map((part, index) => {
        if (typeof part !== 'string') return part;

        return part.split('\n').map((line, lineIndex, arr) => (
            <Fragment key={`text-${index}-${lineIndex}`}>
                {line}
                {lineIndex < arr.length - 1 ? <br /> : null}
            </Fragment>
        ));
    });
}

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
                    {renderMessageContent(message.content)}
                </div>
                <div className="message-time">{time}</div>
            </div>
        </div>
    );
}
