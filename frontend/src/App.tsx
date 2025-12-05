import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatInterface } from './components/ChatInterface';
import { DataExplorer } from './components/DataExplorer';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState<'chat' | 'explorer'>('chat');

  return (
    <div className="flex h-screen w-full bg-gray-50">
      <Sidebar
        onViewChange={setCurrentView}
        currentView={currentView}
      />
      <div className="flex-1 overflow-hidden">
        {currentView === 'chat' ? (
          <ChatInterface />
        ) : (
          <DataExplorer />
        )}
      </div>
    </div>
  );
}

export default App;
