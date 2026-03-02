import { useState, useRef } from 'react';

export default function InputBar({ onSend, onUpload, isLoading }) {
    const [text, setText] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [validationError, setValidationError] = useState(null);
    const fileRef = useRef(null);
    const textareaRef = useRef(null);

    // File validation constants
    const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10MB
    const MAX_PDF_SIZE = 15 * 1024 * 1024;   // 15MB
    const ALLOWED_TYPES = {
        '.pdf': 'application/pdf',
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
        '.png': ['image/png'],
        '.tiff': ['image/tiff'],
        '.tif': ['image/tiff'],
    };

    const validateFile = (file) => {
        // Check file extension
        const fileName = file.name.toLowerCase();
        const fileExtension = fileName.substring(fileName.lastIndexOf('.'));
        
        if (!Object.keys(ALLOWED_TYPES).includes(fileExtension)) {
            setValidationError(`❌ Invalid file type. Only PDF, JPG, PNG, and TIFF are allowed.`);
            return false;
        }

        // Check file size based on type
        const isPdf = fileExtension === '.pdf';
        const maxSize = isPdf ? MAX_PDF_SIZE : MAX_IMAGE_SIZE;
        const maxSizeMB = isPdf ? 15 : 10;

        if (file.size > maxSize) {
            setValidationError(`❌ File too large. ${isPdf ? 'PDFs' : 'Images'} must be under ${maxSizeMB}MB. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.`);
            return false;
        }

        return true;
    };

    const handleSend = () => {
        if (selectedFile) {
            onUpload(selectedFile);
            setSelectedFile(null);
            setValidationError(null);
            return;
        }
        if (!text.trim()) return;
        onSend(text.trim());
        setText('');
        setValidationError(null);
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
            setValidationError(null);
            if (validateFile(file)) {
                setSelectedFile(file);
            } else {
                // Reset file input
                e.target.value = '';
            }
        }
    };

    const formatSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    };

    return (
        <div className="input-area">
            {validationError && (
                <div className="error-message" style={{
                    padding: '10px 12px',
                    marginBottom: '10px',
                    backgroundColor: '#fee',
                    color: '#c33',
                    borderLeft: '4px solid #c33',
                    borderRadius: '4px',
                    fontSize: '0.9rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <span>{validationError}</span>
                    <button
                        onClick={() => setValidationError(null)}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: '#c33',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            padding: 0
                        }}
                    >
                        ✕
                    </button>
                </div>
            )}

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
