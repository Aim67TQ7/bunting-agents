import React, { createContext, useContext, useState, useEffect } from 'react';

interface AIContextType {
  orchestras: Orchestra[];
  systemStatus: SystemStatus;
  submitProblem: (problem: string, requirements?: any) => Promise<string>;
  getTaskStatus: (taskId: string) => Promise<any>;
}

interface Orchestra {
  name: string;
  type: string;
  consciousness_level: string;
  performance: {
    success_rate: number;
    tasks_completed: number;
    avg_response_time: number;
  };
}

interface SystemStatus {
  active_tasks: number;
  completed_tasks: number;
  database_connected: boolean;
}

const AIContext = createContext<AIContextType | undefined>(undefined);

export const AIProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [orchestras, setOrchestras] = useState<Orchestra[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    active_tasks: 0,
    completed_tasks: 0,
    database_connected: false
  });

  const submitProblem = async (problem: string, requirements?: any): Promise<string> => {
    const response = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description: problem, requirements })
    });
    const data = await response.json();
    return data.task_id;
  };

  const getTaskStatus = async (taskId: string) => {
    const response = await fetch(`/api/tasks/${taskId}`);
    return response.json();
  };

  useEffect(() => {
    // Fetch initial data
    fetch('/api/orchestras').then(r => r.json()).then(setOrchestras);
    fetch('/api/system/status').then(r => r.json()).then(setSystemStatus);
    
    // WebSocket connection for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'system_status') {
        setSystemStatus(data.data);
      }
    };
    
    return () => ws.close();
  }, []);

  return (
    <AIContext.Provider value={{ orchestras, systemStatus, submitProblem, getTaskStatus }}>
      {children}
    </AIContext.Provider>
  );
};

export const useAI = () => {
  const context = useContext(AIContext);
  if (!context) {
    throw new Error('useAI must be used within AIProvider');
  }
  return context;
};