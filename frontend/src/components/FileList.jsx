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
                    {files.map(cls => (
                        <li key={cls.classId} className="file-item">
                            <span className="file-icon">📄</span>
                            <span className="file-name">{cls.title || `File ${cls.classId}`}</span>
                            <button
                                className="icon-btn"
                                onClick={() => onDownloadSingle(cls)}
                                title="Download Single File"
                                disabled={downloading}
                                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                            >
                                <Download size={16} />
                            </button>
                        </li>
                    ))}
                </ul>
            ) : (
                <div className="no-items">No items found in this unit.</div>
            )}
        </div>
    );
}

export default FileList;
