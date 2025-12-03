import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { ParliamentView } from './components/ParliamentView';
import { TopicAnalysis } from './components/TopicAnalysis';

export default function App() {
  const [activeTab, setActiveTab] = useState('parliament');

  return (
    <div className="flex h-screen bg-gray-50">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />
      
      <main className="flex-1 overflow-auto">
        {activeTab === 'parliament' && <ParliamentView />}
        {activeTab === 'committees' && (
          <div className="p-8">
            <h1>Semantic Shift</h1>
            <p className="text-gray-600">Yakında...</p>
          </div>
        )}
        {activeTab === 'legislation' && <TopicAnalysis />}
        {activeTab === 'sessions' && (
          <div className="p-8">
            <h1>Oturumlar</h1>
            <p className="text-gray-600">Yakında...</p>
          </div>
        )}
      </main>
    </div>
  );
}
