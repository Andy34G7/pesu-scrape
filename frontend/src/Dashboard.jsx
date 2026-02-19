import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Menu, X } from 'lucide-react';
import Sidebar from './components/Sidebar';
import UnitGrid from './components/UnitGrid';
import FileList from './components/FileList';
import './Dashboard.css';
import CommandPalette from './components/CommandPalette';

function Dashboard() {
    const [courses, setCourses] = useState([]);
    const [selectedCourse, setSelectedCourse] = useState(null);
    const [units, setUnits] = useState([]);
    const [selectedUnit, setSelectedUnit] = useState(null);
    const [classes, setClasses] = useState([]);
    const [loadingCourses, setLoadingCourses] = useState(true);
    const [loadingUnits, setLoadingUnits] = useState(false);
    const [loadingClasses, setLoadingClasses] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortOrder, setSortOrder] = useState('asc');
    const [resourceType, setResourceType] = useState('2'); // '2' for Slides, '3' for Notes
    const [isCmdOpen, setIsCmdOpen] = useState(false);
    const [favorites, setFavorites] = useState(() => {
        const saved = localStorage.getItem('pesu_favorites');
        return saved ? JSON.parse(saved) : [];
    });
    const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    useEffect(() => {
        fetchCourses();

        const handleKeyDown = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                setIsCmdOpen(true);
            }
        };

        window.addEventListener('keydown', handleKeyDown);

        // Triple tap detection
        let lastTap = 0;
        let tapCount = 0;

        const handleTouchStart = (e) => {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;

            if (tapLength < 500 && tapLength > 0) {
                tapCount++;
                if (tapCount === 3) {
                    setIsCmdOpen(true);
                    tapCount = 0; // Reset
                }
            } else {
                tapCount = 1;
            }
            lastTap = currentTime;
        };

        window.addEventListener('touchstart', handleTouchStart);

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            window.removeEventListener('touchstart', handleTouchStart);
        };
    }, []);

    useEffect(() => {
        localStorage.setItem('pesu_favorites', JSON.stringify(favorites));
    }, [favorites]);

    const toggleFavorite = (courseId) => {
        setFavorites(prev => {
            if (prev.includes(courseId)) {
                return prev.filter(id => id !== courseId);
            } else {
                return [...prev, courseId];
            }
        });
    };

    const fetchCourses = async () => {
        try {
            const response = await fetch('/api/courses');
            const data = await response.json();
            if (Array.isArray(data)) {
                setCourses(data);
            } else {
                console.error('Courses data is not an array:', data);
                setCourses([]);
                toast.error('Failed to load courses data');
            }
        } catch (error) {
            console.error('Error fetching courses:', error);
            toast.error('Network error fetching courses');
        } finally {
            setLoadingCourses(false);
        }
    };

    const handleCourseSelect = async (course) => {
        setSelectedCourse(course);
        setSelectedUnit(null);
        setClasses([]);
        setLoadingUnits(true);
        try {
            const cleanId = course.id.replace(/\\|"/g, '');
            const response = await fetch(`/api/units/${cleanId}`);
            const data = await response.json();
            if (Array.isArray(data)) {
                setUnits(data);
            } else {
                console.error('Units data is not an array:', data);
                setUnits([]);
                toast.error('Failed to load units. Please try logging in again.');
            }
        } catch (error) {
            console.error('Error fetching units:', error);
            toast.error('Failed to load units');
        } finally {
            setLoadingUnits(false);
        }
    };

    const handleUnitSelect = async (unit) => {
        setSelectedUnit(unit);
        setLoadingClasses(true);
        try {
            const response = await fetch(`/api/classes/${unit.unitId}`);
            const data = await response.json();
            if (Array.isArray(data)) {
                setClasses(data);
            } else {
                console.error('Classes data is not an array:', data);
                setClasses([]);
                toast.error('Failed to load classes. Please try logging in again.');
            }
        } catch (error) {
            console.error('Error fetching classes:', error);
            toast.error('Failed to load files');
        } finally {
            setLoadingClasses(false);
        }
    };

    const handleDownload = async () => {
        if (!selectedCourse || !selectedUnit || classes.length === 0) return;

        setDownloading(true);
        const toastId = toast.loading(`Preparing ${resourceType === '2' ? 'Slides' : 'Notes'} download...`);

        try {
            const files = classes.map(cls => ({
                classId: cls.classId,
                name: cls.title
            }));

            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    files,
                    course_id: selectedCourse.id,
                    course_name: selectedCourse.subjectName,
                    unit_name: selectedUnit.title,
                    resource_type: resourceType
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${selectedCourse.subjectName}_${selectedUnit.title}_${resourceType === '2' ? 'Slides' : 'Notes'}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
                toast.success('Download started!', { id: toastId });
            } else {
                toast.error('Download failed', { id: toastId });
            }
        } catch (error) {
            console.error('Download error:', error);
            toast.error('Error downloading file', { id: toastId });
        } finally {
            setDownloading(false);
        }
    };

    const handleSingleDownload = async (cls) => {
        const toastId = toast.loading(`Downloading ${cls.title}...`);
        const files = [{
            classId: cls.classId,
            name: cls.title
        }];

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    files,
                    course_id: selectedCourse.id,
                    course_name: selectedCourse.subjectName,
                    unit_name: selectedUnit.title,
                    resource_type: resourceType
                }),
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${cls.title}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                toast.success('Download complete!', { id: toastId });
            } else {
                toast.error('Download failed', { id: toastId });
            }
        } catch (error) {
            console.error('Single download error:', error);
            toast.error('Error downloading file', { id: toastId });
        }
    };

    const filteredCourses = courses
        .filter(course => {
            const matchesSearch = course.subjectName.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesFav = showFavoritesOnly ? favorites.includes(course.id) : true;
            return matchesSearch && matchesFav;
        })
        .sort((a, b) => {
            // Favorites always on top
            const aFav = favorites.includes(a.id);
            const bFav = favorites.includes(b.id);
            if (aFav && !bFav) return -1;
            if (!aFav && bFav) return 1;

            if (sortOrder === 'asc') {
                return a.subjectName.localeCompare(b.subjectName);
            } else {
                return b.subjectName.localeCompare(a.subjectName);
            }
        });

    return (
        <div className="dashboard-container">
            <CommandPalette
                courses={courses}
                onSelectCourse={handleCourseSelect}
                isOpen={isCmdOpen}
                onClose={() => setIsCmdOpen(false)}
            />

            {isSidebarOpen && (
                <div
                    className="mobile-overlay"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}

            <Sidebar
                courses={filteredCourses}
                selectedCourse={selectedCourse}
                onSelectCourse={(course) => {
                    handleCourseSelect(course);
                    setIsSidebarOpen(false); // Close on selection on mobile
                }}
                searchTerm={searchTerm}
                onSearchChange={setSearchTerm}
                sortOrder={sortOrder}
                onSortChange={setSortOrder}
                loading={loadingCourses}
                favorites={favorites}
                onToggleFavorite={toggleFavorite}
                showFavoritesOnly={showFavoritesOnly}
                onToggleShowFavorites={() => setShowFavoritesOnly(prev => !prev)}
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
            />

            <div className="main-content">
                {selectedCourse ? (
                    <>
                        <div className="main-header">
                            <div className="header-left">
                                <button
                                    className="mobile-menu-btn"
                                    onClick={() => setIsSidebarOpen(true)}
                                >
                                    <Menu size={24} />
                                </button>
                                <h1>{selectedCourse.subjectName}</h1>
                            </div>
                            <div className="header-actions">
                                <div className="resource-toggle">
                                    <button
                                        className={`toggle-btn ${resourceType === '2' ? 'active' : ''}`}
                                        onClick={() => {
                                            console.log('Switching to Slides (2)');
                                            setResourceType('2');
                                        }}
                                    >
                                        Slides
                                    </button>
                                    <button
                                        className={`toggle-btn ${resourceType === '3' ? 'active' : ''}`}
                                        onClick={() => {
                                            console.log('Switching to Notes (3)');
                                            setResourceType('3');
                                        }}
                                    >
                                        Notes
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div className="content-area">
                            <UnitGrid
                                units={units}
                                selectedUnit={selectedUnit}
                                onSelectUnit={handleUnitSelect}
                                loading={loadingUnits}
                            />

                            {selectedUnit && (
                                <FileList
                                    files={classes}
                                    loading={loadingClasses}
                                    downloading={downloading}
                                    onDownloadAll={handleDownload}
                                    onDownloadSingle={handleSingleDownload}
                                    resourceType={resourceType}
                                />
                            )}
                        </div>
                    </>
                ) : (
                    <div className="empty-state">
                        <button
                            className="mobile-menu-btn absolute-menu-btn"
                            onClick={() => setIsSidebarOpen(true)}
                        >
                            <Menu size={24} />
                        </button>
                        <div style={{ fontSize: '4rem', marginBottom: '1rem', opacity: 0.2 }}>📚</div>
                        <h3>Select a course to view details</h3>
                        <p style={{ color: 'var(--muted-foreground)', marginBottom: '1.5rem' }}>
                            Choose a course from the sidebar to access slides and notes.
                        </p>
                        <div className="cmd-hint">
                            Press <kbd style={{ background: 'var(--muted)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border)' }}>Ctrl</kbd> + <kbd style={{ background: 'var(--muted)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border)' }}>K</kbd> to search
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default Dashboard;
