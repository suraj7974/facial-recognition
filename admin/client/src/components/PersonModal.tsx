import { useState, useEffect } from 'react';
import type { PersonDetails } from '../services/api';
import { getImageUrl, addImage, deletePerson, deleteImage } from '../services/api';

interface PersonModalProps {
  name: string;
  personData: PersonDetails | null;
  onClose: () => void;
  onPersonDeleted: () => void;
  onImageAdded: () => void;
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

const PersonModal = ({ name, personData, onClose, onPersonDeleted, onImageAdded, showToast }: PersonModalProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [deletingImage, setDeletingImage] = useState<string | null>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${name}" permanently?`)) return;
    
    setIsDeleting(true);
    try {
      const response = await deletePerson(name);
      if (response.success) {
        showToast(response.message || 'Person deleted successfully', 'success');
        if (response.rebuild_started) {
          showToast('Database rebuild started automatically...', 'info');
        }
        onPersonDeleted();
        onClose();
      } else {
        showToast(response.error || 'Failed to delete person', 'error');
      }
    } catch {
      showToast('Failed to delete person', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleAddImage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      showToast('Please select an image', 'warning');
      return;
    }

    setIsAdding(true);
    try {
      const response = await addImage(name, selectedFile);
      if (response.success) {
        showToast(response.message || 'Image added successfully', 'success');
        if (response.rebuild_started) {
          showToast('Database rebuild started automatically...', 'info');
        }
        setSelectedFile(null);
        // Reset file input
        const fileInput = document.querySelector('.add-image-form input[type="file"]') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
        onImageAdded();
      } else {
        showToast(response.error || 'Failed to add image', 'error');
      }
    } catch {
      showToast('Failed to add image', 'error');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteImage = async (filename: string) => {
    if (!confirm(`Delete image "${filename}"?`)) return;
    
    setDeletingImage(filename);
    try {
      const response = await deleteImage(name, filename);
      if (response.success) {
        showToast('Image deleted successfully', 'success');
        if (response.rebuild_started) {
          showToast('Database rebuild started automatically...', 'info');
        }
        onImageAdded(); // Refresh the modal data
      } else {
        showToast(response.error || 'Failed to delete image', 'error');
      }
    } catch {
      showToast('Failed to delete image', 'error');
    } finally {
      setDeletingImage(null);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{name}</h2>
          <button className="modal-close" onClick={onClose}>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <div className="modal-body">
          <h4 style={{ marginBottom: '0.75rem', fontWeight: 600 }}>Information</h4>
          <div className="person-info">
            {personData?.info || 'No information provided.'}
          </div>

          <h4 style={{ marginBottom: '0.75rem', fontWeight: 600 }}>
            Images ({personData?.images?.length || 0})
          </h4>
          {personData?.images && personData.images.length > 0 ? (
            <div className="person-images">
              {personData.images.map((img) => (
                <div key={img} className="person-image-card">
                  <img src={getImageUrl(name, img)} alt={img} />
                  <div className="image-actions">
                    <button 
                      className="btn-delete"
                      onClick={() => handleDeleteImage(img)}
                      disabled={deletingImage === img}
                      title="Delete image"
                    >
                      {deletingImage === img ? (
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="spin">
                          <path d="M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z"/>
                        </svg>
                      ) : (
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                        </svg>
                      )}
                    </button>
                  </div>
                  <p>{img}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '1.5rem' }}>
              <p>No images found for this person.</p>
            </div>
          )}

          <div className="add-image-section">
            <h4>Add Image</h4>
            <form className="add-image-form" onSubmit={handleAddImage}>
              <input
                type="file"
                accept="image/*"
                className="file-input"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
              <button type="submit" className="btn btn-primary" disabled={isAdding || !selectedFile}>
                {isAdding ? 'Adding...' : 'Add'}
              </button>
            </form>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-danger" onClick={handleDelete} disabled={isDeleting}>
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
            </svg>
            {isDeleting ? 'Deleting...' : 'Delete Person'}
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default PersonModal;
