import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Sun, Moon } from 'lucide-react';

function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isDark, setIsDark] = useState(() => {
        if (typeof window !== 'undefined') {
            return document.documentElement.classList.contains('dark') ||
                localStorage.getItem('theme') === 'dark' ||
                (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
        }
        return true;
    });

    useEffect(() => {
        if (isDark) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [isDark]);

    useEffect(() => {
        const savedCreds = localStorage.getItem('pesu_creds');
        if (savedCreds) {
            try {
                const { u, p } = JSON.parse(atob(savedCreds));
                setUsername(u);
                setPassword(p);
                setRememberMe(true);
            } catch (e) {
                localStorage.removeItem('pesu_creds');
            }
        }
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        const toastId = toast.loading('Logging in...');

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (response.ok) {
                if (rememberMe) {
                    const creds = btoa(JSON.stringify({ u: username, p: password }));
                    localStorage.setItem('pesu_creds', creds);
                } else {
                    localStorage.removeItem('pesu_creds');
                }
                toast.success(data.message, { id: toastId });
                onLogin(data.message);
            } else {
                const msg = data.message || 'Login failed';
                setError(msg);
                toast.error(msg, { id: toastId });
            }
        } catch (err) {
            const msg = 'Network error. Please try again.';
            setError(msg);
            toast.error(msg, { id: toastId });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-container relative">
            <button
                onClick={() => setIsDark(!isDark)}
                className="absolute top-4 left-4 p-2 rounded-full bg-secondary text-foreground hover:bg-accent transition-colors cursor-pointer"
                title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
                {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            <form className="login-card" onSubmit={handleSubmit}>
                <div className="login-header">
                    <h1>PESU Academy Login</h1>
                    <p>Enter your credentials to continue</p>
                </div>

                {error && (
                    <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-lg mb-4 text-center border border-destructive/20">
                        {error}
                    </div>
                )}

                <div className="form-group">
                    <label htmlFor="username">Username (SRN)</label>
                    <input
                        type="text"
                        id="username"
                        value={username}
                        onChange={(e) => {
                            setUsername(e.target.value);
                            setError('');
                        }}
                        required
                        placeholder="Enter your SRN"
                        className="form-input rounded-full px-4"
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={(e) => {
                            setPassword(e.target.value);
                            setError('');
                        }}
                        required
                        placeholder="Enter your password"
                        className="form-input rounded-full px-4"
                    />
                </div>

                <div className="form-group checkbox-group">
                    <label className="checkbox-label">
                        <input
                            type="checkbox"
                            checked={rememberMe}
                            onChange={(e) => setRememberMe(e.target.checked)}
                        />
                        Remember me (saves locally)
                    </label>
                </div>

                <button type="submit" className="login-btn rounded-full" disabled={loading}>
                    {loading ? 'Logging in...' : 'Login'}
                </button>
            </form>
        </div>
    );
}

export default Login;
