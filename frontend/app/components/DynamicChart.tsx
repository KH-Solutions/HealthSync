"use client";

import React from 'react';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, TooltipProps, XAxis, YAxis } from 'recharts';
import { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent';

export interface ChartData {
    date: string;
    [key: string]: number | string;
}

interface DynamicChartProps {
    data: ChartData[];
    type: 'bar' | 'line';
    dataKey: string;
    color: string;
    title: string;
    unit: string;
}

const formatHoursDecimal = (hoursDecimal: number): string => {
    const hours = Math.floor(hoursDecimal);
    const minutes = Math.round((hoursDecimal - hours) * 60);
    return `${hours}h ${minutes}m`;
};

const CustomTooltip = ({ active, payload, label }: TooltipProps<ValueType, NameType>) => {
    if (active && payload && payload.length) {
        const dataPoint = payload[0];
        let displayValue: string;

        if (dataPoint.unit === 'h') {
            displayValue = formatHoursDecimal(dataPoint.value as number);
        } else {
            displayValue = `${dataPoint.value} ${dataPoint.unit || ''}`;
        }

        return (
            <div className="p-2 bg-gray-700 border border-gray-600 rounded shadow-lg text-white">
                <p className="label font-semibold">{`${label}`}</p>
                <p className="intro" style={{ color: dataPoint.color || '#FFFFFF' }}>
                    {`${dataPoint.name}: ${displayValue}`}
                </p>
            </div>
        );
    }
    return null;
};

const DynamicChart: React.FC<DynamicChartProps> = ({ data, type, dataKey, color, title, unit }) => {
    const renderChart = () => {
        if (type === 'bar') {
            return (
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
                        <XAxis dataKey="date" stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} />
                        <YAxis stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} />
                        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(128, 128, 128, 0.1)' }} />
                        <Bar dataKey={dataKey} fill={color} name={title} unit={unit} />
                    </BarChart>
                </ResponsiveContainer>
            );
        }

        if (type === 'line') {
            return (
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
                        <XAxis dataKey="date" stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} />
                        <YAxis stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(128, 128, 128, 0.2)', strokeWidth: 1 }} />
                        <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} name={title} unit={unit} />
                    </LineChart>
                </ResponsiveContainer>
            );
        }

        return null;
    };

    return (
        <div style={{ width: '100%', height: 300 }}>
            {renderChart()}
        </div>
    );
};

export default DynamicChart;