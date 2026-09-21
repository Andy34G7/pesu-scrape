import React, { useState } from 'react';
import { X, Download, CheckCircle2, XCircle, HelpCircle, Copy, Check, RefreshCw, BookOpen, Award, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

function McqModal({ isOpen, onClose, course, unit, classItem, mcqsData, loading }) {
    const [mode, setMode] = useState('study'); // 'study' (show answers) or 'practice' (interactive quiz)
    const [userAnswers, setUserAnswers] = useState({}); // { [questionIndex]: optionIndex }
    const [copied, setCopied] = useState(false);

    if (!isOpen) return null;

    const questions = mcqsData?.questions || [];
    const count = questions.length;

    const handleSelectOption = (qIdx, optIdx) => {
        if (mode !== 'practice') return;
        setUserAnswers(prev => ({
            ...prev,
            [qIdx]: optIdx
        }));
    };

    const resetPractice = () => {
        setUserAnswers({});
        toast.success('Quiz reset!');
    };

    // Calculate score in practice mode
    const answeredCount = Object.keys(userAnswers).length;
    let correctCount = 0;
    Object.entries(userAnswers).forEach(([qIdx, optIdx]) => {
        const q = questions[parseInt(qIdx)];
        if (q && q.options[optIdx]?.isCorrect) {
            correctCount++;
        }
    });

    const generateMarkdown = () => {
        let md = `# ${course?.subjectName || 'Course'} - ${classItem?.title || 'Class'} MCQs\n`;
        md += `**Unit:** ${unit?.title || 'Unit'}\n`;
        md += `**Total Questions:** ${count}\n\n`;
        md += `---\n\n`;

        questions.forEach((q, idx) => {
            md += `### ${q.serial || `${idx + 1})`} ${q.question}\n\n`;
            q.options.forEach((opt, optIdx) => {
                const letter = String.fromCharCode(65 + optIdx);
                const mark = opt.isCorrect ? ' **[CORRECT]**' : '';
                md += `- (${letter}) ${opt.option}${mark}\n`;
            });
            md += `\n`;
        });
        return md;
    };

    const handleDownloadMd = () => {
        const md = generateMarkdown();
        const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const safeName = (classItem?.title || 'MCQs').replace(/[^\w\-\.]/g, '_');
        a.download = `${safeName}_MCQs.md`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(url);
        a.remove();
        toast.success('Markdown file downloaded!');
    };

    const handleDownloadJson = () => {
        const jsonStr = JSON.stringify(mcqsData, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const safeName = (classItem?.title || 'MCQs').replace(/[^\w\-\.]/g, '_');
        a.download = `${safeName}_MCQs.json`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(url);
        a.remove();
        toast.success('JSON file downloaded!');
    };

    const handleCopy = async () => {
        try {
            const md = generateMarkdown();
            await navigator.clipboard.writeText(md);
            setCopied(true);
            toast.success('Copied Markdown to clipboard!');
            setTimeout(() => setCopied(false), 2000);
        } catch {
            toast.error('Failed to copy to clipboard');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
            <div
                className="relative w-full max-w-4xl max-h-[90vh] bg-card text-card-foreground rounded-2xl shadow-2xl border border-border flex flex-col overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Modal Header */}
                <div className="p-5 border-b border-border flex items-center justify-between bg-secondary/40">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
                            <BookOpen size={22} />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-foreground leading-tight">
                                {classItem?.title || 'Class'} — MCQs
                            </h2>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {course?.subjectName} &bull; {count} Question{count === 1 ? '' : 's'}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                        title="Close"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Mode Switcher & Actions Bar */}
                <div className="px-5 py-3 border-b border-border bg-background flex flex-wrap items-center justify-between gap-3 text-sm">
                    {/* View Mode Toggle */}
                    <div className="inline-flex rounded-lg p-1 bg-secondary border border-border">
                        <button
                            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                                mode === 'study'
                                    ? 'bg-card text-foreground shadow-xs'
                                    : 'text-muted-foreground hover:text-foreground'
                            }`}
                            onClick={() => setMode('study')}
                        >
                            📖 Study Mode (Answers Revealed)
                        </button>
                        <button
                            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                                mode === 'practice'
                                    ? 'bg-card text-foreground shadow-xs'
                                    : 'text-muted-foreground hover:text-foreground'
                            }`}
                            onClick={() => setMode('practice')}
                        >
                            🎯 Practice Quiz Mode
                        </button>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-2">
                        {mode === 'practice' && (
                            <button
                                onClick={resetPractice}
                                className="px-2.5 py-1.5 rounded-lg border border-border bg-secondary/50 text-foreground hover:bg-secondary text-xs font-medium flex items-center gap-1.5 transition-colors"
                                title="Reset answers"
                            >
                                <RefreshCw size={13} />
                                Reset Quiz
                            </button>
                        )}
                        <button
                            onClick={handleCopy}
                            className="px-2.5 py-1.5 rounded-lg border border-border bg-secondary/50 text-foreground hover:bg-secondary text-xs font-medium flex items-center gap-1.5 transition-colors"
                            title="Copy Markdown"
                        >
                            {copied ? <Check size={13} className="text-green-500" /> : <Copy size={13} />}
                            {copied ? 'Copied' : 'Copy'}
                        </button>
                        <button
                            onClick={handleDownloadMd}
                            className="px-2.5 py-1.5 rounded-lg border border-border bg-secondary/50 text-foreground hover:bg-secondary text-xs font-medium flex items-center gap-1.5 transition-colors"
                            title="Download Markdown file"
                        >
                            <Download size={13} />
                            .MD
                        </button>
                        <button
                            onClick={handleDownloadJson}
                            className="px-2.5 py-1.5 rounded-lg border border-border bg-secondary/50 text-foreground hover:bg-secondary text-xs font-medium flex items-center gap-1.5 transition-colors"
                            title="Download JSON file"
                        >
                            <FileText size={13} />
                            .JSON
                        </button>
                    </div>
                </div>

                {/* Practice Mode Score Banner */}
                {mode === 'practice' && count > 0 && (
                    <div className="px-5 py-2.5 bg-primary/5 border-b border-primary/10 flex items-center justify-between text-xs font-medium text-foreground">
                        <div className="flex items-center gap-2">
                            <Award size={16} className="text-primary" />
                            <span>
                                Answered: <strong>{answeredCount}</strong> / {count}
                            </span>
                        </div>
                        <div>
                            Score:{' '}
                            <span className="font-bold text-green-600 dark:text-green-400">
                                {correctCount}
                            </span>{' '}
                            correct ({answeredCount > 0 ? Math.round((correctCount / answeredCount) * 100) : 0}%)
                        </div>
                    </div>
                )}

                {/* Modal Body / Questions List */}
                <div className="p-6 overflow-y-auto flex-1 space-y-6">
                    {loading ? (
                        <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
                            <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
                            <p className="text-sm font-medium">Fetching MCQs from PESU Academy...</p>
                        </div>
                    ) : count === 0 ? (
                        <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
                            <HelpCircle size={40} className="opacity-30 mb-2" />
                            <h3 className="text-base font-semibold text-foreground">No MCQs Found</h3>
                            <p className="text-xs max-w-sm">
                                There are no online multiple-choice questions uploaded for this class.
                            </p>
                        </div>
                    ) : (
                        questions.map((q, qIdx) => {
                            const selectedOptIdx = userAnswers[qIdx];
                            const isAnswered = selectedOptIdx !== undefined;
                            const isCorrect = isAnswered && q.options[selectedOptIdx]?.isCorrect;

                            return (
                                <div
                                    key={qIdx}
                                    className="p-4 sm:p-5 rounded-xl bg-secondary/30 border border-border/80 transition-all"
                                >
                                    {/* Question Text */}
                                    <div className="flex items-start gap-3 mb-4">
                                        <span className="inline-flex items-center justify-center px-2 py-0.5 rounded-md bg-secondary text-foreground text-xs font-bold shrink-0">
                                            {q.serial || `Q${qIdx + 1}`}
                                        </span>
                                        <p className="text-sm sm:text-base font-medium text-foreground leading-relaxed">
                                            {q.question}
                                        </p>
                                    </div>

                                    {/* Options */}
                                    <div className="space-y-2.5 pl-2 sm:pl-4">
                                        {q.options.map((opt, optIdx) => {
                                            const letter = String.fromCharCode(65 + optIdx);
                                            const isThisSelected = selectedOptIdx === optIdx;

                                            let optionClass = 'bg-card border-border hover:bg-secondary/60 text-foreground';
                                            let icon = null;

                                            if (mode === 'study') {
                                                if (opt.isCorrect) {
                                                    optionClass = 'bg-green-500/10 border-green-500/50 text-green-700 dark:text-green-300 font-medium';
                                                    icon = <CheckCircle2 size={16} className="text-green-600 dark:text-green-400 shrink-0" />;
                                                }
                                            } else if (mode === 'practice' && isAnswered) {
                                                if (opt.isCorrect) {
                                                    optionClass = 'bg-green-500/10 border-green-500/50 text-green-700 dark:text-green-300 font-medium';
                                                    icon = <CheckCircle2 size={16} className="text-green-600 dark:text-green-400 shrink-0" />;
                                                } else if (isThisSelected && !opt.isCorrect) {
                                                    optionClass = 'bg-red-500/10 border-red-500/50 text-red-700 dark:text-red-300 font-medium';
                                                    icon = <XCircle size={16} className="text-red-600 dark:text-red-400 shrink-0" />;
                                                }
                                            } else if (mode === 'practice' && isThisSelected) {
                                                optionClass = 'bg-primary/10 border-primary text-foreground font-medium';
                                            }

                                            return (
                                                <div
                                                    key={optIdx}
                                                    onClick={() => handleSelectOption(qIdx, optIdx)}
                                                    className={`p-3 rounded-lg border text-xs sm:text-sm flex items-center justify-between gap-3 transition-all ${
                                                        mode === 'practice' && !isAnswered ? 'cursor-pointer hover:border-primary/50' : ''
                                                    } ${optionClass}`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <span className="w-5 h-5 rounded-full bg-secondary flex items-center justify-center font-bold text-xs shrink-0 text-muted-foreground">
                                                            {letter}
                                                        </span>
                                                        <span className="leading-snug">{opt.option}</span>
                                                    </div>
                                                    {icon}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                {/* Modal Footer */}
                <div className="px-5 py-3.5 border-t border-border bg-secondary/40 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground font-medium">
                        PESU Academy Course On Demand MCQs
                    </span>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 text-xs font-semibold shadow-xs transition-opacity"
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
}

export default McqModal;
