import React from 'react';
import { Download, BookOpen, FileQuestion } from 'lucide-react';

function FileList({ files, loading, downloading, onDownloadAll, onDownloadSingle, onViewMcqs, resourceType }) {
    const isMcqMode = resourceType === '8';
    const isNotesMode = resourceType === '3';
    const resourceName = isMcqMode ? 'MCQs' : (isNotesMode ? 'notes' : 'slides');

    return (
        <div className="classes-section">
            <div className="section-header">
                <h3>
                    {isMcqMode ? 'MCQs & Quizzes' : `Files (${isNotesMode ? 'Notes' : 'Slides'})`}
                </h3>
                <button
                    className="download-btn"
                    onClick={onDownloadAll}
                    disabled={downloading || files.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                    <Download size={16} />
                    {downloading
                        ? 'Processing...'
                        : isMcqMode
                        ? 'Download All Unit MCQs (.md)'
                        : 'Download All Merged'}
                </button>
            </div>

            {loading ? (
                <div className="loading">
                    {isMcqMode ? 'Loading MCQs & topics...' : 'Loading files...'}
                </div>
            ) : files.length > 0 ? (
                <ul className="file-list">
                    {files.map(cls => {
                        let isUnavailable = false;
                        if (isMcqMode) {
                            isUnavailable = cls.hasMCQs === false;
                        } else if (isNotesMode) {
                            isUnavailable = cls.hasNotes === false;
                        } else {
                            isUnavailable = cls.hasSlides === false;
                        }

                        return (
                            <li key={cls.classId} className={`file-item ${isUnavailable ? 'opacity-60' : ''}`}>
                                <span className="file-icon">
                                    {isUnavailable ? '⚠️' : isMcqMode ? '📝' : '📄'}
                                </span>
                                <span className="file-name" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    {cls.title || `Topic ${cls.classId}`}
                                    {isUnavailable && (
                                        <span style={{ fontSize: '0.75rem', opacity: 0.7, fontStyle: 'italic' }}>
                                            (No {resourceName})
                                        </span>
                                    )}
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    {isMcqMode && (
                                        <button
                                            className="icon-btn"
                                            onClick={() => onViewMcqs && onViewMcqs(cls)}
                                            title={isUnavailable ? "No MCQs uploaded for this topic" : "View & Practice MCQs"}
                                            disabled={isUnavailable}
                                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                        >
                                            <BookOpen size={16} />
                                        </button>
                                    )}
                                    <button
                                        className="icon-btn"
                                        onClick={() => onDownloadSingle(cls)}
                                        title={
                                            isUnavailable
                                                ? `No ${resourceName} uploaded for this class`
                                                : isMcqMode
                                                ? "Download MCQs (.md)"
                                                : "Download Single File"
                                        }
                                        disabled={downloading || isUnavailable}
                                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                    >
                                        <Download size={16} />
                                    </button>
                                </div>
                            </li>
                        );
                    })}
                </ul>
            ) : (
                <div className="no-items">No items found in this unit.</div>
            )}
        </div>
    );
}

export default FileList;
