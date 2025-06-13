"use client";

import React from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export interface ChartDataPoint {
    date: string;
    value: number;
}

interface LineChartComponentProps {
    data: ChartDataPoint[];
    dataKey: string;
    lineColor: string;
    unit: string;
}

const LineChartComponent: React.FC<LineChartComponentProps> = ({ data, dataKey, lineColor, unit }) => {
    return (
        <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
                <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
                    <XAxis dataKey="date" stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} />
                    <YAxis stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} unit={unit} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#2D3748', border: 'none', color: '#E2E8F0' }}
                        labelStyle={{ color: '#A0AEC0' }}
                        formatter={(value: number) => [`${value} ${unit}`, null]}
                    />
                    <Line type="monotone" dataKey={dataKey} stroke={lineColor} strokeWidth={2} dot={false} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default LineChartComponent;