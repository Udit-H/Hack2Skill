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

export async function panicWipe(sessionId, userId) {
    const res = await fetch(`${API_BASE}/panic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, user_id: userId }),
    });
    return res.ok;
}

/**
 * Download a draft PDF via fetch → blob → save-as dialog.
 * Resolves relative /api/ paths against the correct backend base URL.
 * @param {string} href - The link href, e.g. "/api/drafts/session/file.pdf"
 */
export async function downloadDraft(href) {
    // Absolute URLs (S3 presigned) use directly; relative /api/ paths resolve via API_BASE
    let url;
    if (href.startsWith('http://') || href.startsWith('https://')) {
        url = href;  // S3 presigned URL — use as-is
    } else if (href.startsWith('/api')) {
        url = `${API_BASE}${href.replace(/^\/api/, '')}`;
    } else {
        url = href;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error(`Download failed (${res.status})`);

    // Validate we actually got a PDF back, not an HTML error page / SPA shell
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('text/html')) {
        throw new Error(
            'Server returned HTML instead of PDF. The backend API may be unreachable.'
        );
    }

    // Force blob type to application/pdf regardless of server header
    const raw = await res.arrayBuffer();
    const blob = new Blob([raw], { type: 'application/pdf' });

    // Ensure filename always ends in .pdf
    let filename = href.split('/').pop() || 'document.pdf';
    if (!filename.endsWith('.pdf')) {
        filename = filename.replace(/\.[^.]+$/, '') + '.pdf';
    }

    // Create a temporary <a> to trigger browser save-as
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();

    // Cleanup
    setTimeout(() => {
        URL.revokeObjectURL(anchor.href);
        document.body.removeChild(anchor);
    }, 100);
}
