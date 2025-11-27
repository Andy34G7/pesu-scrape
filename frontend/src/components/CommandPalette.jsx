import React, { useState, useEffect, useRef } from 'react';

import './CommandPalette.css';

function CommandPalette({ courses, onSelectCourse, isOpen, onClose }) {
    const [query, setQuery] = useState('');
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef(null);
    const listRef = useRef(null);

    const filteredCourses = courses.filter(course =>
        course.subjectName.toLowerCase().includes(query.toLowerCase()) ||
        (course.id && course.id.toLowerCase().includes(query.toLowerCase()))
    ).slice(0, 10); // Limit to 10 results

    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 50);
            setQuery('');
            setSelectedIndex(0);
        }
    }, [isOpen]);

    useEffect(() => {
        setSelectedIndex(0);
    }, [query]);

    const handleKeyDown = (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex(prev => (prev + 1) % filteredCourses.length);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex(prev => (prev - 1 + filteredCourses.length) % filteredCourses.length);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (filteredCourses[selectedIndex]) {
                onSelectCourse(filteredCourses[selectedIndex]);
                onClose();
            }
        } else if (e.key === 'Escape') {
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="cmd-overlay" onClick={onClose}>
            <div className="cmd-modal" onClick={e => e.stopPropagation()}>
                <div className="cmd-search-wrapper">
                    <span className="cmd-icon">🔍</span>
                    <input
                        ref={inputRef}
                        type="text"
                        className="cmd-input"
                        placeholder="Search for a course..."
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                    <span className="cmd-esc">ESC</span>
                </div>
                {filteredCourses.length > 0 ? (
                    <ul className="cmd-list" ref={listRef}>
                        {filteredCourses.map((course, index) => {
                            // Parse course code for display
                            const match = course.subjectName.match(/^([A-Z]{2}\d{2}[A-Z]{2,3}\d{3}[A-Z]?)\s*-\s*(.+)$/);
                            let displayName = course.subjectName;
                            let displayCode = "";
                            if (match) {
                                displayCode = match[1];
                                displayName = match[2];
                            }

                            return (
                                <li
                                    key={course.id}
                                    className={`cmd-item ${index === selectedIndex ? 'selected' : ''}`}
                                    onClick={() => {
                                        onSelectCourse(course);
                                        onClose();
                                    }}
                                    onMouseEnter={() => setSelectedIndex(index)}
                                >
                                    {displayCode && <span className="cmd-course-code">{displayCode}</span>}
                                    <span className="cmd-course-name">{displayName}</span>
                                </li>
                            );
                        })}
                    </ul>
                ) : (
                    <div className="cmd-empty">No results found.</div>
                )}
            </div>
        </div>
    );
}

export default CommandPalette;
