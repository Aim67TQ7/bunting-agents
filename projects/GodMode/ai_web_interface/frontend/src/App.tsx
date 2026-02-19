import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AIProvider } from './contexts/AIContext';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Orchestras from './pages/Orchestras';
import Header from './components/Header';
import './App.css';

function App() {
  return (
    <AIProvider>
      <Router>
        <div className="min-h-screen bg-gray-900 text-white">
          <Header />
          <main className="container mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/orchestras" element={<Orchestras />} />
            </Routes>
          </main>
        </div>
      </Router>
    </AIProvider>
  );
}

export default App;