import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, rebuildDatabase, getRebuildStatus } from '../services/api';
import type { RebuildStatus, StatsResponse } from '../types';

interface DashboardProps {
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

const Dashboard = ({ showToast }: DashboardProps) => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [rebuildStatus, setRebuildStatus] = useState<RebuildStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const pollIntervalRef = useRef<number | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const data = await getStats();
      setStats(data);
      setRebuildStatus(data.rebuild_status);
      return data.rebuild_status;
    } catch {
      showToast('Failed to load dashboard data', 'error');
      return null;
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const pollRebuildStatus = useCallback(async () => {
    try {
      const status = await getRebuildStatus();
      setRebuildStatus(status);
      
      if (status.status === 'completed' || status.status === 'failed') {
        await loadStats();
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        
        if (status.status === 'completed') {
          showToast(status.message || 'Database rebuild completed!', 'success');
        } else if (status.status === 'failed') {
          showToast(status.message || 'Database rebuild failed', 'error');
        }
      }
      
      return status;
    } catch {
      return null;
    }
  }, [loadStats, showToast]);

  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;
    
    pollIntervalRef.current = window.setInterval(() => {
      pollRebuildStatus();
    }, 1000);
  }, [pollRebuildStatus]);

  useEffect(() => {
    loadStats().then((status) => {
      if (status?.is_rebuilding) {
        startPolling();
      }
    });

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [loadStats, startPolling]);

  const handleRebuild = async () => {
    if (rebuildStatus?.is_rebuilding) {
      showToast('Rebuild already in progress', 'warning');
      return;
    }

    try {
      const response = await rebuildDatabase();
      if (response.success) {
        showToast('Database rebuild started...', 'info');
        startPolling();
      } else {
        showToast(`Failed to start rebuild: ${response.error || 'Unknown error'}`, 'error');
      }
    } catch {
      showToast('Failed to start database rebuild', 'error');
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusInfo = (status: string) => {
    switch (status) {
      case 'completed': return { color: 'var(--success)', label: 'Synced', icon: '✓' };
      case 'failed': return { color: 'var(--danger)', label: 'Failed', icon: '✕' };
      case 'rebuilding': return { color: 'var(--warning)', label: 'Building', icon: '↻' };
      case 'reloading': return { color: 'var(--warning)', label: 'Reloading', icon: '↻' };
      default: return { color: 'var(--success)', label: 'Ready', icon: '●' };
    }
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-content">
          <div className="spinner large"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusInfo(rebuildStatus?.status || 'idle');

  return (
    <div className="dashboard">
      {/* Hero Section */}
      <div className="dashboard-hero">
        <div className="hero-content">
          <h1>Welcome to Face Admin</h1>
          <p>Manage your criminal detection database with ease</p>
        </div>
        <div className="hero-status">
          <div 
            className={`status-badge ${rebuildStatus?.is_rebuilding ? 'pulsing' : ''}`}
            style={{ backgroundColor: statusInfo.color }}
          >
            <span className="status-icon">{statusInfo.icon}</span>
            <span>{statusInfo.label}</span>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="dashboard-stats">
        <div className="stat-card-modern">
          <div className="stat-icon blue">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats?.total_identities || 0}</span>
            <span className="stat-label">Identities</span>
          </div>
          <div className="stat-trend">
            <span className="trend-label">In database</span>
          </div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-icon green">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats?.total_images || 0}</span>
            <span className="stat-label">Images</span>
          </div>
          <div className="stat-trend">
            <span className="trend-label">Total uploaded</span>
          </div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-icon purple">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20 13H4c-.55 0-1 .45-1 1v6c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-6c0-.55-.45-1-1-1zM7 19c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zM20 3H4c-.55 0-1 .45-1 1v6c0 .55.45 1 1 1h16c.55 0 1-.45 1-1V4c0-.55-.45-1-1-1zM7 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value">{stats?.database.exists ? formatBytes(stats.database.size) : 'N/A'}</span>
            <span className="stat-label">Database</span>
          </div>
          <div className="stat-trend">
            <span className="trend-label">{stats?.database.exists ? 'Active' : 'Not found'}</span>
          </div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-icon orange">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
            </svg>
          </div>
          <div className="stat-info">
            <span className="stat-value" style={{ fontSize: '1.5rem' }}>
              {stats?.total_identities ? Math.round(stats.total_images / stats.total_identities * 10) / 10 : 0}
            </span>
            <span className="stat-label">Avg Images</span>
          </div>
          <div className="stat-trend">
            <span className="trend-label">Per identity</span>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        {/* Sync Status Card */}
        <div className="dashboard-card sync-card">
          <div className="card-header-modern">
            <div className="header-title">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
              </svg>
              <span>Database Sync</span>
            </div>
            <div 
              className={`sync-indicator ${rebuildStatus?.is_rebuilding ? 'syncing' : ''}`}
              style={{ backgroundColor: statusInfo.color }}
            />
          </div>
          
          <div className="sync-content">
            {rebuildStatus?.is_rebuilding ? (
              <div className="sync-progress-section">
                <div className="progress-circle">
                  <svg viewBox="0 0 36 36">
                    <path
                      className="progress-bg"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="progress-bar"
                      strokeDasharray={`${rebuildStatus.progress}, 100`}
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <span className="progress-value">{rebuildStatus.progress}%</span>
                </div>
                <div className="sync-details">
                  <span className="sync-status">{rebuildStatus.message}</span>
                  <span className="sync-time">In progress...</span>
                </div>
              </div>
            ) : (
              <div className="sync-idle-section">
                <div className="sync-check">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                  </svg>
                </div>
                <div className="sync-details">
                  <span className="sync-status">Database is up to date</span>
                  <span className="sync-time">Auto-sync enabled</span>
                </div>
              </div>
            )}
          </div>

          <div className="sync-actions">
            <button 
              className="btn-modern"
              onClick={handleRebuild}
              disabled={rebuildStatus?.is_rebuilding}
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
              </svg>
              {rebuildStatus?.is_rebuilding ? 'Rebuilding...' : 'Force Rebuild'}
            </button>
            <button className="btn-modern secondary" onClick={() => loadStats()}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
              </svg>
              Refresh
            </button>
          </div>
        </div>

        {/* Quick Actions Card */}
        <div className="dashboard-card actions-card">
          <div className="card-header-modern">
            <div className="header-title">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
              <span>Quick Actions</span>
            </div>
          </div>
          
          <div className="quick-actions-grid">
            <button className="quick-action-btn" onClick={() => navigate('/enroll')}>
              <div className="action-icon add">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm-9-2V7H4v3H1v2h3v3h2v-3h3v-2H6zm9 4c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
              </div>
              <span className="action-label">Add Person</span>
              <span className="action-desc">Enroll new identity</span>
            </button>

            <button className="quick-action-btn" onClick={() => navigate('/identities')}>
              <div className="action-icon view">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                </svg>
              </div>
              <span className="action-label">View All</span>
              <span className="action-desc">Browse identities</span>
            </button>

            <button className="quick-action-btn" onClick={() => navigate('/logs')}>
              <div className="action-icon logs">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                </svg>
              </div>
              <span className="action-label">View Logs</span>
              <span className="action-desc">System activity</span>
            </button>

            <button className="quick-action-btn" onClick={handleRebuild} disabled={rebuildStatus?.is_rebuilding}>
              <div className="action-icon sync">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
              </div>
              <span className="action-label">Sync DB</span>
              <span className="action-desc">Rebuild database</span>
            </button>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="info-banner">
        <div className="info-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
          </svg>
        </div>
        <div className="info-content">
          <strong>Auto-Sync Enabled</strong>
          <span>The database automatically rebuilds when you add, update, or delete identities. No manual action needed.</span>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
