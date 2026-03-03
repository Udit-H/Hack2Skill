import { useState, useRef, useEffect } from 'react';

export default function InputBar({ onSend, onUpload, isLoading }) {
    const [text, setText] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const fileRef = useRef(null);
    const textareaRef = useRef(null);
    const prevIsLoading = useRef(isLoading);

    // Auto-focus on mount and when loading finishes
    useEffect(() => {
        if (prevIsLoading.current && !isLoading) {
            textareaRef.current?.focus();
        }
        prevIsLoading.current = isLoading;
    }, [isLoading]);

    useEffect(() => {
        // Initial focus
        textareaRef.current?.focus();
    }, []);

    const handleSend = () => {
        if (selectedFile) {
            onUpload(selectedFile);
            setSelectedFile(null);
            return;
        }
        if (!text.trim()) return;
        onSend(text.trim());
        setText('');
        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleTextareaInput = (e) => {
        setText(e.target.value);
        // Auto-resize
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
    };

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
        }
    };

    const formatSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <div className="input-area">
            {selectedFile && (
                <div className="file-preview">
                    <div style={{ fontSize: '1.4rem' }}>📄</div>
                    <div className="file-preview-info">
                        <div className="file-preview-name">{selectedFile.name}</div>
                        <div className="file-preview-size">{formatSize(selectedFile.size)}</div>
                    </div>
                    <button
                        className="file-preview-remove"
                        onClick={() => setSelectedFile(null)}
                        aria-label="Remove file"
                    >
                        ✕
                    </button>
                </div>
            )}

            <div className="input-wrapper">
                <textarea
                    ref={textareaRef}
                    rows={1}
                    value={text}
                    onChange={handleTextareaInput}
                    onKeyDown={handleKeyDown}
                    placeholder="Tell me what happened..."
                    disabled={isLoading}
                    aria-label="Type your message"
                />

                <div className="input-actions">
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".pdf,.jpg,.jpeg,.png,.tiff"
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                    />
                    <button
                        className="input-action-btn"
                        onClick={() => fileRef.current?.click()}
                        title="Upload document"
                        aria-label="Upload document"
                    >
                        📎
                    </button>
                    <button
                        className="input-action-btn send"
                        onClick={handleSend}
                        disabled={isLoading || (!text.trim() && !selectedFile)}
                        title="Send message"
                        aria-label="Send message"
                    >
                        ➤
                    </button>
                </div>
            </div>

            <div className="input-disclaimer">
                Your data stays on this device. Sahayak provides legal guidance, not legal advice.
            </div>
        </div>
    );
}
