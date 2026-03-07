const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE = configuredBase
    ? `${configuredBase.replace(/\/$/, '')}/api`
    : '/api';

export async function createSession(userId = null) {
    const options = { method: 'POST' };
    if (userId) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify({ user_id: userId });
    }
    const res = await fetch(`${API_BASE}/session`, options);
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
}

export async function listUserSessions(userId) {
    const res = await fetch(`${API_BASE}/sessions/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) throw new Error('Failed to list sessions');
    return res.json();
}

export async function loadSession(sessionId, userId) {
    const res = await fetch(`${API_BASE}/sessions/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, user_id: userId }),
    });
    if (!res.ok) throw new Error('Failed to load session');
    return res.json();
}

export async function sendMessage(sessionId, message, language = 'en', coords = null, userId = null) {
    const body = { session_id: sessionId, message, language };
    if (coords) {
        body.latitude = coords.latitude;
        body.longitude = coords.longitude;
    }
    if (userId) {
        body.user_id = userId;
    }
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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
