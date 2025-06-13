import React from 'react';

interface HealthDataCardProps {
    title: string;
    value: string;
    unit: string;
    isClickable?: boolean;
    onClick?: () => void;
    isActive?: boolean;
    children?: React.ReactNode;
}

const HealthDataCard: React.FC<HealthDataCardProps> = ({ title, value, unit, isClickable, onClick, isActive, children }) => {
    const baseClasses = "bg-gray-800 p-6 rounded-lg shadow-lg w-full transition-all duration-300";
    const clickableClasses = isClickable ? "cursor-pointer hover:bg-gray-700" : "";
    const activeClasses = isActive ? "ring-2 ring-blue-500 bg-gray-700" : "";

    return (
        <div className={`${baseClasses} ${clickableClasses} ${activeClasses}`} onClick={onClick}>
            <div>
                <div className="flex justify-between items-start">
                    <h3 className="text-lg font-semibold text-gray-400">{title}</h3>
                </div>
                {!children && (
                    <div className="flex items-baseline space-x-2 mt-2">
                        <p className="text-4xl font-bold text-white">{value}</p>
                        <span className="text-gray-300">{unit}</span>
                    </div>
                )}
            </div>

            {children && <div className="mt-4">{children}</div>}
        </div>
    );
};

export default HealthDataCard;