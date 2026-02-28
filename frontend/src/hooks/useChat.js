import { useState, useCallback, useRef, useEffect } from 'react';
import { createSession, sendMessage, uploadDocument } from '../utils/api';

export function useChat() {
    const [messages, setMessages] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [agentInfo, setAgentInfo] = useState({
        activeAgent: 'legal',
        workflowStatus: 'awaiting_docs',
    });
    const initialized = useRef(false);

    // Initialize session on mount
    useEffect(() => {
        if (initialized.current) return;
        initialized.current = true;

        createSession()
            .then((data) => {
                setSessionId(data.session_id);
            })
            .catch((err) => {
                console.error('Session init failed:', err);
                // Fallback: generate a local ID
                setSessionId(`local-${Date.now().toString(36)}`);
            });
    }, []);

    const send = useCallback(
        async (text) => {
            if (!text.trim() || isLoading) return;
            setError(null);

            const userMsg = {
                id: Date.now(),
                role: 'user',
                content: text,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, userMsg]);
            setIsLoading(true);

            try {
                const response = await sendMessage(sessionId, text);

                const assistantMsg = {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: response.reply,
                    timestamp: new Date(),
                };
                setMessages((prev) => [...prev, assistantMsg]);

                if (response.agent_info) {
                    setAgentInfo(response.agent_info);
                }
            } catch (err) {
                setError('Could not get a response. Please try again.');
                console.error('Chat error:', err);
            } finally {
                setIsLoading(false);
            }
        },
        [sessionId, isLoading]
    );

    const upload = useCallback(
        async (file) => {
            if (!file || isLoading) return;
            setError(null);
            setIsLoading(true);

            const userMsg = {
                id: Date.now(),
                role: 'user',
                content: `📎 Uploaded: ${file.name}`,
                timestamp: new Date(),
                isUpload: true,
            };
            setMessages((prev) => [...prev, userMsg]);

            try {
                const response = await uploadDocument(sessionId, file);

                const assistantMsg = {
                    id: Date.now() + 1,
                    role: 'assistant',
                    content:
                        response.reply ||
                        'Document received. I am analyzing it now.',
                    timestamp: new Date(),
                };
                setMessages((prev) => [...prev, assistantMsg]);

                if (response.agent_info) {
                    setAgentInfo(response.agent_info);
                }
            } catch (err) {
                setError('Document upload failed. Please try again.');
                console.error('Upload error:', err);
            } finally {
                setIsLoading(false);
            }
        },
        [sessionId, isLoading]
    );

    const clearMessages = useCallback(() => {
        setMessages([]);
        setAgentInfo({ activeAgent: 'legal', workflowStatus: 'awaiting_docs' });
    }, []);

    return {
        messages,
        sessionId,
        isLoading,
        error,
        agentInfo,
        send,
        upload,
        clearMessages,
    };
}
