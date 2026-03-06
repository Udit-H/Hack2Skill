import { useState, useCallback, useRef, useEffect } from 'react';
import { createSession, sendMessage, uploadDocument, loadSession } from '../utils/api';
import { useLanguage } from './useLanguage.jsx';
import { useAuth } from './useAuth.jsx';

export function useChat() {
    const [messages, setMessages] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const { language } = useLanguage();
    const { user } = useAuth();
    const [agentInfo, setAgentInfo] = useState({
        activeAgent: 'legal',
        workflowStatus: 'awaiting_docs',
    });
    const initialized = useRef(false);
    const userCoords = useRef(null);

    // Get user ID from authenticated user
    // Cognito user object has userId or username field
    // For anonymous users, generate a browser-specific ID
    const getUserId = () => {
        if (user?.userId || user?.username || user?.signInDetails?.loginId) {
            return user.userId || user.username || user.signInDetails.loginId;
        }
        
        // For anonymous users, use localStorage-based ID
        let anonId = localStorage.getItem('sahayak_anon_id');
        if (!anonId) {
            anonId = `anon-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            localStorage.setItem('sahayak_anon_id', anonId);
        }
        return anonId;
    };
    
    const userId = getUserId();
    
    // Debug logging
    useEffect(() => {
        console.log('🔍 User object:', user);
        console.log('🆔 Extracted userId:', userId);
    }, [user, userId]);

    // Request GPS location once on mount
    useEffect(() => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    userCoords.current = {
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                    };
                    console.log('📍 GPS acquired:', userCoords.current);
                },
                (err) => console.log('📍 GPS unavailable, will use text fallback:', err.message),
                { enableHighAccuracy: true, timeout: 10000 }
            );
        }
    }, []);

    // Initialize session on mount
    useEffect(() => {
        if (initialized.current) return;
        initialized.current = true;

        createSession(userId)
            .then((data) => {
                setSessionId(data.session_id);
            })
            .catch((err) => {
                console.error('Session init failed:', err);
                // Fallback: generate a local ID
                setSessionId(`local-${Date.now().toString(36)}`);
            });
    }, [userId]);

    const loadExistingSession = useCallback(
        async (existingSessionId) => {
            if (!userId) return;
            setIsLoading(true);
            setError(null);

            try {
                const data = await loadSession(existingSessionId, userId);
                setSessionId(data.session_id);
                
                // Convert DynamoDB messages to UI format
                const loadedMessages = data.messages.map((msg, idx) => ({
                    id: Date.now() + idx,
                    role: msg.role,
                    content: msg.content,
                    timestamp: new Date(msg.timestamp),
                }));
                
                setMessages(loadedMessages);
                
                if (data.agent_info) {
                    setAgentInfo(data.agent_info);
                }
            } catch (err) {
                setError('Failed to load session');
                console.error('Load session error:', err);
            } finally {
                setIsLoading(false);
            }
        },
        [userId]
    );

    const createNewSession = useCallback(async () => {
        setIsLoading(true);
        try {
            const data = await createSession(userId);
            setSessionId(data.session_id);
            setMessages([]);
            setAgentInfo({
                activeAgent: 'legal',
                workflowStatus: 'awaiting_docs',
            });
        } catch (err) {
            console.error('Failed to create new session:', err);
            setSessionId(`local-${Date.now().toString(36)}`);
        } finally {
            setIsLoading(false);
        }
    }, [userId]);

    const send = useCallback(
        async (text) => {
            if (!text.trim() || isLoading || !sessionId) return;
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
                const response = await sendMessage(sessionId, text, language, userCoords.current, userId);

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
        [sessionId, isLoading, language]
    );

    const upload = useCallback(
        async (file) => {
            if (!file || isLoading) return;
            setError(null);

            // File validation
            const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
            const MAX_PDF_SIZE = 15 * 1024 * 1024;   // 15MB
            const ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'];

            // Check file extension
            const fileName = file.name.toLowerCase();
            const fileExtension = fileName.substring(fileName.lastIndexOf('.'));
            
            if (!ALLOWED_EXTENSIONS.includes(fileExtension)) {
                setError('❌ Invalid file type. Only PDF, JPG, PNG, and TIFF files are allowed.');
                return;
            }

            // Check file size
            const isPdf = fileExtension === '.pdf';
            const maxSize = isPdf ? MAX_PDF_SIZE : MAX_IMAGE_SIZE;
            const maxSizeMB = isPdf ? 15 : 10;

            if (file.size > maxSize) {
                setError(`❌ File too large. ${isPdf ? 'PDFs' : 'Images'} must be under ${maxSizeMB}MB. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.`);
                return;
            }

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
        userId,
        send,
        upload,
        clearMessages,
        loadExistingSession,
        createNewSession,
    };
}
