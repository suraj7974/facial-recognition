import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { enrollPerson } from '../services/api';

interface EnrollProps {
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

const Enroll = ({ showToast }: EnrollProps) => {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [info, setInfo] = useState('');
  const [files, setFiles] = useState<FileList | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      showToast('Person name cannot be empty.', 'warning');
      return;
    }

    if (!files || files.length === 0) {
      showToast('Please select at least one image.', 'warning');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await enrollPerson(name.trim(), info, files);
      if (response.success) {
        showToast(response.message || 'Person enrolled successfully', 'success');
        
        // Show rebuild notification
        if (response.rebuild_started) {
          showToast('Database rebuild started automatically...', 'info');
        }
        
        setName('');
        setInfo('');
        setFiles(null);
        // Reset file input
        const fileInput = document.getElementById('enrollFiles') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
        // Navigate to identities
        navigate('/identities');
      } else {
        showToast(response.error || 'Enrollment failed', 'error');
      }
    } catch {
      showToast('Failed to enroll person', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Enroll New Person</h1>
      </div>

      <div className="card" style={{ maxWidth: '600px' }}>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="enrollName" className="form-label">Person Name</label>
            <input
              id="enrollName"
              type="text"
              className="form-input"
              placeholder="Enter name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="enrollInfo" className="form-label">Info (optional)</label>
            <textarea
              id="enrollInfo"
              className="form-textarea"
              placeholder="Add some details about the person (e.g., criminal record, description)"
              value={info}
              onChange={(e) => setInfo(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="enrollFiles" className="form-label">Images</label>
            <input
              id="enrollFiles"
              type="file"
              className="file-input"
              accept="image/*"
              multiple
              onChange={(e) => setFiles(e.target.files)}
              required
            />
            {files && files.length > 0 && (
              <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                {files.length} file(s) selected
              </p>
            )}
          </div>

          <button 
            type="submit" 
            className="btn btn-success"
            disabled={isSubmitting}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
            {isSubmitting ? 'Creating...' : 'Create & Upload'}
          </button>
        </form>

        <div className="info-text" style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: 'var(--bg)', borderRadius: '8px' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            After enrollment, the face database will automatically rebuild to include the new identity.
            This process runs in the background and typically takes a few seconds.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Enroll;
