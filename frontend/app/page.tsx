// w frontend/app/page.tsx

"use client";

import { useState, useEffect } from "react";

// Definiujemy "kształt" naszych danych za pomocą interfejsów.
// To jest serce TypeScriptu - kontrakt mówiący, jak wyglądają nasze obiekty.
interface User {
    id: number;
    email: string;
}

interface SyncDetails {
    [key: string]: string; // Obiekt z dowolnymi kluczami, ale wartościami typu string
}

export default function Home() {
    // Używamy generycznego useState<Typ>, aby zdefiniować kształt stanu.
    // Teraz TypeScript wie, że `user` może być obiektem typu User lub null.
    const [user, setUser] = useState<User | null>(null);
    const [syncDetails, setSyncDetails] = useState<SyncDetails | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const handleLogin = () => {
        window.location.href = "http://localhost:8000/auth/google/login";
    };

    const handleSync = async () => {
        if (!user) return;
        setIsLoading(true);
        setSyncDetails(null);
        try {
            // TypeScript wie, że user.id musi istnieć, jeśli user nie jest null.
            const response = await fetch(`http://localhost:8000/users/${user.id}/sync?days=7`, {
                method: 'POST',
            });
            const data = await response.json();
            if (response.ok) {
                setSyncDetails(data.details);
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            // TypeScript wie, że 'error' jest typu 'unknown', więc bezpieczniej jest go rzutować.
            if (error instanceof Error) {
                alert(`An error occurred: ${error.message}`);
            }
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const userIdStr = params.get("user_id");
        const email = params.get("email");

        if (userIdStr && email) {
            // TypeScript wyłapałby tu błąd! `id` w naszym interfejsie jest liczbą,
            // a `userIdStr` jest stringiem. Musimy go skonwertować!
            const userData: User = { id: Number(userIdStr), email: email };

            setUser(userData);
            localStorage.setItem("health_sync_user", JSON.stringify(userData));
            window.history.replaceState({}, document.title, "/");
        } else {
            const storedUser = localStorage.getItem("health_sync_user");
            if (storedUser) {
                // Możemy "powiedzieć" TS, jakiego typu danych się spodziewamy po parsowaniu.
                setUser(JSON.parse(storedUser) as User);
            }
        }
    }, []);

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gray-900 text-white">
            <div className="text-center">
                <h1 className="text-5xl font-bold mb-4">Health Sync</h1>
                <p className="text-xl text-gray-400 mb-8">Twoje centrum danych o zdrowiu.</p>

                {!user ? (
                    <button
                        onClick={handleLogin}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg text-lg transition-colors"
                    >
                        Zaloguj się z Google
                    </button>
                ) : (
                    <div className="bg-gray-800 p-8 rounded-lg shadow-lg">
                        <p className="text-lg mb-4">Zalogowano jako: <strong className="text-blue-400">{user.email}</strong></p>
                        <button
                            onClick={handleSync}
                            disabled={isLoading}
                            className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg text-lg transition-colors disabled:bg-gray-500"
                        >
                            {isLoading ? 'Synchronizowanie...' : 'Synchronizuj ostatnie 7 dni'}
                        </button>
                        {syncDetails && (
                            <div className="mt-6 text-left bg-gray-700 p-4 rounded">
                                <h3 className="font-bold mb-2">Wyniki synchronizacji:</h3>
                                <pre className="text-sm whitespace-pre-wrap">
                                    {JSON.stringify(syncDetails, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </main>
    );
}