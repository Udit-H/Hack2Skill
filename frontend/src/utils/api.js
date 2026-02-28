const API_BASE = '/api';

export async function createSession() {
    const res = await fetch(`${API_BASE}/session`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
}

export async function sendMessage(sessionId, message, language = 'en') {
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message, language }),
    });
    if (!res.ok) throw new Error('Failed to send message');
    return res.json();
}

export async function uploadDocument(sessionId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload');
    return res.json();
}

export async function getSession(sessionId) {
    const res = await fetch(`${API_BASE}/session/${sessionId}`);
    if (!res.ok) throw new Error('Failed to get session');
    return res.json();
}

export async function panicWipe(sessionId) {
    const res = await fetch(`${API_BASE}/panic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
    });
    return res.ok;
}
