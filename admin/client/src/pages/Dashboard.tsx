import { useState, useEffect, useCallback, useRef } from 'react';
import { getStats, rebuildDatabase, getRebuildStatus } from '../services/api';
import type { RebuildStatus, StatsResponse } from '../types';

interface DashboardProps {
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

const Dashboard = ({ showToast }: DashboardProps) => {
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
      
      // If rebuild just completed, refresh full stats
      if (status.status === 'completed' || status.status === 'failed') {
        await loadStats();
        // Stop polling
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

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'var(--success)';
      case 'failed': return 'var(--danger)';
      case 'rebuilding':
      case 'reloading': return 'var(--warning)';
      default: return 'var(--text-muted)';
    }
  };

  const getTriggeredByLabel = (triggeredBy: string | null): string => {
    switch (triggeredBy) {
      case 'enroll': return 'New Enrollment';
      case 'delete': return 'Identity Deleted';
      case 'add_image': return 'Image Added';
      case 'delete_image': return 'Image Deleted';
      case 'manual': return 'Manual Trigger';
      default: return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
            </svg>
            Total Identities
          </div>
          <div className="stat-card-value">{stats?.total_identities || 0}</div>
        </div>

        <div className="stat-card success">
          <div className="stat-card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
            </svg>
            Total Images
          </div>
          <div className="stat-card-value">{stats?.total_images || 0}</div>
        </div>

        <div className="stat-card warning">
          <div className="stat-card-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 20h20v-4H2v4zm2-3h2v2H4v-2zM2 4v4h20V4H2zm4 3H4V5h2v2zm-4 7h20v-4H2v4zm2-3h2v2H4v-2z"/>
            </svg>
            Database Size
          </div>
          <div className="stat-card-value" style={{ fontSize: '1.25rem' }}>
            {stats?.database.exists ? formatBytes(stats.database.size) : 'Not Found'}
          </div>
        </div>
      </div>

      {/* Rebuild Status Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">Database Sync Status</div>
        
        <div className="rebuild-status">
          <div className="rebuild-status-indicator">
            <div 
              className="status-dot"
              style={{ 
                backgroundColor: getStatusColor(rebuildStatus?.status || 'idle'),
                animation: rebuildStatus?.is_rebuilding ? 'pulse 1.5s infinite' : 'none'
              }}
            />
            <span className="status-label" style={{ color: getStatusColor(rebuildStatus?.status || 'idle') }}>
              {rebuildStatus?.status?.toUpperCase() || 'IDLE'}
            </span>
          </div>

          {rebuildStatus?.is_rebuilding && (
            <div className="rebuild-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${rebuildStatus.progress}%` }}
                />
              </div>
              <span className="progress-text">{rebuildStatus.progress}%</span>
            </div>
          )}

          <div className="rebuild-message">
            {rebuildStatus?.message || 'System is idle'}
          </div>

          {rebuildStatus?.triggered_by && rebuildStatus.status !== 'idle' && (
            <div className="rebuild-meta">
              <span>Triggered by: {getTriggeredByLabel(rebuildStatus.triggered_by)}</span>
              {rebuildStatus.started_at && (
                <span>Started: {formatDate(rebuildStatus.started_at)}</span>
              )}
              {rebuildStatus.completed_at && (
                <span>Completed: {formatDate(rebuildStatus.completed_at)}</span>
              )}
            </div>
          )}

          {rebuildStatus?.last_error && (
            <div className="rebuild-error">
              Error: {rebuildStatus.last_error}
            </div>
          )}
        </div>
      </div>

      {/* Actions Card */}
      <div className="card">
        <div className="card-header">System Actions</div>
        <div className="action-buttons">
          <button 
            className="btn btn-warning" 
            onClick={handleRebuild}
            disabled={rebuildStatus?.is_rebuilding}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/>
            </svg>
            {rebuildStatus?.is_rebuilding ? 'Rebuilding...' : 'Manual Rebuild'}
          </button>
          
          <button 
            className="btn btn-secondary"
            onClick={() => loadStats()}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
            Refresh
          </button>
        </div>

        <div className="info-text" style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          <p>The database automatically rebuilds when you add, update, or delete identities.</p>
          <p>Use manual rebuild only if the automatic sync fails.</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
