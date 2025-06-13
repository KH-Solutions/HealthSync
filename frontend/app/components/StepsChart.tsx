"use client";

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface StepsDataPoint {
  date: string;
  steps: number;
}

interface StepsChartProps {
  data: StepsDataPoint[];
}

const StepsChart: React.FC<StepsChartProps> = ({ data }) => {
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#4A5568" />
          <XAxis 
            dataKey="date" 
            stroke="#A0AEC0"
            tick={{ fill: '#A0AEC0' }} 
          />
          <YAxis stroke="#A0AEC0" tick={{ fill: '#A0AEC0' }} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#2D3748', border: 'none', color: '#E2E8F0' }}
            labelStyle={{ color: '#A0AEC0' }}
          />
          <Bar dataKey="steps" fill="#4299E1" name="Kroki" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default StepsChart;