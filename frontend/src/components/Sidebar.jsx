import React from 'react';
import { Star, Search, X } from 'lucide-react'; // Added X icon

function Sidebar({
    courses,
    selectedCourse,
    onSelectCourse,
    searchTerm,
    onSearchChange,
    sortOrder,
    onSortChange,
    loading,
    favorites,
    onToggleFavorite,
    showFavoritesOnly,
    onToggleShowFavorites,
    isOpen,
    onClose
}) {
    return (
        <div className={`sidebar ${isOpen ? 'open' : ''}`}>
            <div className="sidebar-header">
                <h2>Courses</h2>
                <button
                    className={`fav-filter-btn ${showFavoritesOnly ? 'active' : ''}`}
                    onClick={onToggleShowFavorites}
                    title="Show Favorites Only"
                >
                    <Star size={18} fill={showFavoritesOnly ? "currentColor" : "none"} />
                </button>
                {/* Mobile Close Button */}
                <button
                    className="mobile-close-btn"
                    onClick={onClose}
                >
                    <X size={20} />
                </button>
            </div>
            <div className="search-sort-controls">
                <div className="search-wrapper" style={{ position: 'relative', flex: 1 }}>
                    <Search
                        size={18}
                        className="search-icon"
                        style={{
                            position: 'absolute',
                            left: '12px',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            color: 'var(--muted-foreground)',
                            pointerEvents: 'none'
                        }}
                    />
                    <input
                        type="text"
                        placeholder="Search courses..."
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.target.value)}
                        className="search-input"
                        style={{ paddingLeft: '38px' }}
                    />
                </div>
                <button
                    onClick={() => onSortChange(prev => prev === 'asc' ? 'desc' : 'asc')}
                    className="sort-btn"
                    title="Sort Courses"
                >
                    Sort: {sortOrder === 'asc' ? 'A-Z' : 'Z-A'}
                </button>
            </div>
            {loading ? (
                <div className="loading">Loading courses...</div>
            ) : (
                <ul className="course-list">
                    {courses.map(course => {
                        const isFav = favorites.includes(course.id);
                        // Parse course code and name
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
                                className={`course-item ${selectedCourse?.id === course.id ? 'active' : ''} ${isFav ? 'favorite' : ''}`}
                                onClick={() => onSelectCourse(course)}
                            >
                                <div className="course-info">
                                    {displayCode ? (
                                        <>
                                            <span className="course-code">{displayCode}</span>
                                            <span className="course-name">{displayName}</span>
                                        </>
                                    ) : (
                                        <span className="course-name">{course.subjectName}</span>
                                    )}
                                </div>
                                <button
                                    className="fav-icon-btn"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onToggleFavorite(course.id);
                                    }}
                                >
                                    <Star
                                        size={16}
                                        className={`fav-icon ${isFav ? 'filled' : ''}`}
                                        fill={isFav ? "currentColor" : "none"}
                                    />
                                </button>
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}

export default Sidebar;
