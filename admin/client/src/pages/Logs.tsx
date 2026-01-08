import { useState, useEffect } from 'react';
import { getLatestLog } from '../services/api';

interface LogsProps {
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

const Logs = ({ showToast }: LogsProps) => {
  const [logContent, setLogContent] = useState('No logs yet');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const response = await getLatestLog();
      setLogContent(response.content || 'No logs found');
    } catch {
      showToast('Could not fetch logs from server.', 'warning');
      setLogContent('Error loading log.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>System Logs</h1>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Latest Log</h3>
          <button 
            className="btn btn-outline" 
            onClick={loadLogs}
            disabled={isLoading}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
            {isLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : (
          <pre className="log-container">{logContent}</pre>
        )}
      </div>
    </div>
  );
};

export default Logs;
