"use client";

import React, { useState, useEffect, useCallback } from 'react';
import HealthDataCard from './HealthDataCard';
import DynamicChart, { ChartData } from './DynamicChart';

type ChartType = 'steps' | 'heart_rate' | 'sleep';

type User = {
    id: number;
    email: string;
};

type DashboardProps = {
    user: User;
    onLogout: () => void; 
};

type HealthDataPoint = {
    timestamp: string;
    value: number;
};

type SleepSummary = {
    data_available: boolean;
    total_duration_minutes?: number;
};

type DailySleepData = {
    date: string;
    total_duration_minutes: number;
};

const Dashboard: React.FC<DashboardProps> = ({ user, onLogout }) => {
    // --- Component State Hooks ---
    const [syncDetails, setSyncDetails] = useState<Record<string, string> | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [stepsData, setStepsData] = useState<HealthDataPoint[]>([]);
    const [heartRateData, setHeartRateData] = useState<HealthDataPoint[]>([]);
    const [sleepSummary, setSleepSummary] = useState<SleepSummary | null>(null);
    const [sleepHistory, setSleepHistory] = useState<DailySleepData[]>([]);
    const [activeChart, setActiveChart] = useState<ChartType>('steps');

    // --- Data fetching and synchronization logic ---
    const fetchStoredData = useCallback(async () => {
        if (!user) return;
        try {
            // Use Promise.all to send all data requests simultaneously
            const [stepsResponse, heartRateResponse, sleepSummaryResponse, sleepHistoryResponse] = await Promise.all([
                fetch(`http://localhost:8000/users/${user.id}/data/steps`),
                fetch(`http://localhost:8000/users/${user.id}/data/heart_rate`),
                fetch(`http://localhost:8000/users/${user.id}/data/sleep/summary`),
                fetch(`http://localhost:8000/users/${user.id}/data/sleep`)
            ]);
            
            if (stepsResponse.ok) setStepsData(await stepsResponse.json());
            if (heartRateResponse.ok) setHeartRateData(await heartRateResponse.json());
            if (sleepSummaryResponse.ok) setSleepSummary(await sleepSummaryResponse.json());
            if (sleepHistoryResponse.ok) setSleepHistory(await sleepHistoryResponse.json());
        } catch (error) {
            console.error("Wystąpił błąd podczas pobierania danych:", error);
        }
    }, [user]);

    useEffect(() => {
        const loadInitialData = async () => {
            setIsLoading(true);
            await fetchStoredData();
            setIsLoading(false);
        }
        loadInitialData();
    }, [fetchStoredData]);

    const handleSync = async () => {
        setIsLoading(true);
        setSyncDetails(null);
        try {
            const syncResponse = await fetch(`http://localhost:8000/users/${user.id}/sync?days=30`, { method: 'POST' });
            const syncData = await syncResponse.json();
            if (!syncResponse.ok) throw new Error(syncData.message || "Błąd synchronizacji");
            setSyncDetails(syncData.details);

            await fetchStoredData();
        } catch (error) {
            console.error("Błąd synchronizacji:", error);
            if (error instanceof Error) alert(`Błąd synchronizacji: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    const formatSleepDuration = (totalMinutes?: number): string => {
        if (typeof totalMinutes !== 'number' || totalMinutes <= 0) return "--";
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        return `${hours}h ${minutes}m`;
    };

    const formatDataForChart = (data: (HealthDataPoint[] | DailySleepData[]), dataType: ChartType): ChartData[] => {
        return data.map(item => {
            let value: number;
            if (dataType === 'sleep' && 'total_duration_minutes' in item) {
                value = parseFloat((item.total_duration_minutes / 60).toFixed(2));
            } else {
                value = Math.round('value' in item ? item.value : 0);
            }

            return {
                date: new Date('date' in item ? item.date : item.timestamp).toLocaleDateString('pl-PL', { day: '2-digit', month: '2-digit' }),
                value: value,
            };
        });
    };

    const totalSteps = stepsData.reduce((sum, item) => sum + item.value, 0);
    const latestHeartRate = heartRateData.length > 0 ? Math.round(heartRateData[heartRateData.length - 1].value) : "--";
    const sleepDisplayValue = formatSleepDuration(sleepSummary?.total_duration_minutes);
    const sleepUnit = sleepDisplayValue === '--' ? 'h m' : '';

    return (
        <div className="w-full max-w-6xl bg-gray-900 p-8 rounded-lg shadow-lg">
            <div className="flex flex-wrap justify-between items-center gap-4 mb-8">
                <div>
                    <h2 className="text-2xl font-bold">Panel Główny</h2>
                    <p className="text-gray-400">Zalogowano jako: {user.email}</p>
                </div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={onLogout}
                        className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
                    >
                        Wyloguj
                    </button>
                    <button
                        onClick={handleSync}
                        disabled={isLoading}
                        className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-lg transition-colors disabled:bg-gray-500 disabled:cursor-not-allowed"
                    >
                        {isLoading ? 'Przetwarzanie...' : 'Odśwież dane'}
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <HealthDataCard
                    title="Suma kroków (30 dni)"
                    value={totalSteps.toLocaleString('pl-PL')}
                    unit="kroków"
                    isClickable={stepsData.length > 0}
                    onClick={() => setActiveChart('steps')}
                    isActive={activeChart === 'steps'}
                />
                <HealthDataCard
                    title="Tętno (ostatnie)"
                    value={String(latestHeartRate)}
                    unit="bpm"
                    isClickable={heartRateData.length > 0}
                    onClick={() => setActiveChart('heart_rate')}
                    isActive={activeChart === 'heart_rate'}
                />
                <HealthDataCard
                    title="Ostatni sen"
                    value={sleepDisplayValue}
                    unit={sleepUnit}
                    isClickable={sleepHistory.length > 0}
                    onClick={() => setActiveChart('sleep')}
                    isActive={activeChart === 'sleep'}
                />
            </div>

            <div className="mt-8">
                {activeChart === 'steps' && stepsData.length > 0 && (
                    <HealthDataCard title="Aktywność dzienna (kroki)" value="" unit="">
                        <DynamicChart data={formatDataForChart(stepsData, 'steps')} type="bar" dataKey="value" color="#4299E1" title="Kroki" unit="kroków" />
                    </HealthDataCard>
                )}
                {activeChart === 'heart_rate' && heartRateData.length > 0 && (
                    <HealthDataCard title="Historia tętna" value="" unit="">
                        <DynamicChart data={formatDataForChart(heartRateData, 'heart_rate')} type="line" dataKey="value" color="#F56565" title="Tętno" unit="bpm" />
                    </HealthDataCard>
                )}
                {activeChart === 'sleep' && sleepHistory.length > 0 && (
                    <HealthDataCard title="Historia snu (ostatnie 30 dni)" value="" unit="">
                        <DynamicChart
                            data={formatDataForChart(sleepHistory, 'sleep')}
                            type="bar"
                            dataKey="value"
                            color="#A78BFA"
                            title="Sen"
                            unit="h"
                        />
                    </HealthDataCard>
                )}
                {((activeChart === 'steps' && stepsData.length === 0) ||
                    (activeChart === 'heart_rate' && heartRateData.length === 0) ||
                    (activeChart === 'sleep' && sleepHistory.length === 0)) && !isLoading && (
                        <div className="text-center text-gray-500 p-10 bg-gray-800 rounded-lg">
                            <p>Brak danych do wyświetlenia. Spróbuj najpierw zsynchronizować dane.</p>
                        </div>
                    )}
            </div>

            {syncDetails && (
                <div className="mt-8 text-left bg-gray-700 p-4 rounded text-xs">
                    <h3 className="font-bold mb-2">Ostatnie szczegóły synchronizacji:</h3>
                    <pre className="whitespace-pre-wrap">{JSON.stringify(syncDetails, null, 2)}</pre>
                </div>
            )}
        </div>
    );
};

export default Dashboard;