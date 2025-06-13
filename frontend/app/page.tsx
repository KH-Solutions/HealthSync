"use client";

import { useState, useEffect } from "react";
import Dashboard from "./components/Dashboard"; // Importujemy nasz nowy komponent

interface User {
    id: number;
    email: string;
}

export default function Home() {
    const [user, setUser] = useState<User | null>(null);

    const handleLogin = () => {
        window.location.href = "http://localhost:8000/auth/google/login";
    };

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const userIdStr = params.get("user_id");
        const email = params.get("email");

        if (userIdStr && email) {
            const userData: User = { id: Number(userIdStr), email: email };
            setUser(userData);
            localStorage.setItem("health_sync_user", JSON.stringify(userData));
            window.history.replaceState({}, document.title, "/");
        } else {
            const storedUser = localStorage.getItem("health_sync_user");
            if (storedUser) {
                setUser(JSON.parse(storedUser) as User);
            }
        }
    }, []);

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gray-900 text-white">
            {!user ? (
                <div className="text-center">
                    <h1 className="text-5xl font-bold mb-4">Health Sync</h1>
                    <p className="text-xl text-gray-400 mb-8">Twoje centrum danych o zdrowiu.</p>
                    <button
                        onClick={handleLogin}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg text-lg transition-colors"
                    >
                        Zaloguj się z Google
                    </button>
                </div>
            ) : (
                <Dashboard user={user} />
            )}
        </main>
    );
}