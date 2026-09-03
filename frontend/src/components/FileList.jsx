import React from 'react';
import { Download } from 'lucide-react';

function FileList({ files, loading, downloading, onDownloadAll, onDownloadSingle, resourceType }) {
    return (
        <div className="classes-section">
            <div className="section-header">
                <h3>Files ({resourceType === '3' ? 'Notes' : 'Slides'})</h3>
                <button
                    className="download-btn"
                    onClick={onDownloadAll}
                    disabled={downloading || files.length === 0}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                    <Download size={16} />
                    {downloading ? 'Processing...' : 'Download All Merged'}
                </button>
            </div>

            {loading ? (
                <div className="loading">Loading files...</div>
            ) : files.length > 0 ? (
                <ul className="file-list">
                    {files.map(cls => {
                        const isUnavailable = resourceType === '3' ? cls.hasNotes === false : cls.hasSlides === false;
                        const resourceName = resourceType === '3' ? 'notes' : 'slides';
                        return (
                            <li key={cls.classId} className={`file-item ${isUnavailable ? 'opacity-60' : ''}`}>
                                <span className="file-icon">{isUnavailable ? '⚠️' : '📄'}</span>
                                <span className="file-name" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    {cls.title || `File ${cls.classId}`}
                                    {isUnavailable && (
                                        <span style={{ fontSize: '0.75rem', opacity: 0.7, fontStyle: 'italic' }}>
                                            (No {resourceName})
                                        </span>
                                    )}
                                </span>
                                <button
                                    className="icon-btn"
                                    onClick={() => onDownloadSingle(cls)}
                                    title={isUnavailable ? `No ${resourceName} uploaded for this class` : "Download Single File"}
                                    disabled={downloading || isUnavailable}
                                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                                >
                                    <Download size={16} />
                                </button>
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
