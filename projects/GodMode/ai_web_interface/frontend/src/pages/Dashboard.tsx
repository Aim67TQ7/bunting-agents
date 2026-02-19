import React from 'react';
import { useAI } from '../contexts/AIContext';
import OrchestraCard from '../components/OrchestraCard';
import SystemMetrics from '../components/SystemMetrics';

const Dashboard: React.FC = () => {
  const { orchestras, systemStatus } = useAI();

  return (
    <div className="space-y-8">
      <h1 className="text-4xl font-bold text-center bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
        🎭 AI Orchestra Control Center
      </h1>
      
      <SystemMetrics status={systemStatus} />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {orchestras.map((orchestra) => (
          <OrchestraCard key={orchestra.name} orchestra={orchestra} />
        ))}
      </div>
    </div>
  );
};

export default Dashboard;