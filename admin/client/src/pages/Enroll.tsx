import { useState, useRef, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { enrollPerson } from '../services/api';

interface EnrollProps {
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

interface PreviewImage {
  file: File;
  preview: string;
}

const Enroll = ({ showToast }: EnrollProps) => {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [info, setInfo] = useState('');
  const [images, setImages] = useState<PreviewImage[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [currentStep, setCurrentStep] = useState(1);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    
    const newImages: PreviewImage[] = [];
    Array.from(files).forEach((file) => {
      if (file.type.startsWith('image/')) {
        newImages.push({
          file,
          preview: URL.createObjectURL(file)
        });
      }
    });
    
    setImages((prev) => [...prev, ...newImages]);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const removeImage = (index: number) => {
    setImages((prev) => {
      const newImages = [...prev];
      URL.revokeObjectURL(newImages[index].preview);
      newImages.splice(index, 1);
      return newImages;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      showToast('Please enter a name', 'warning');
      setCurrentStep(1);
      return;
    }

    if (images.length === 0) {
      showToast('Please add at least one image', 'warning');
      setCurrentStep(2);
      return;
    }

    setIsSubmitting(true);
    try {
      // Create a FileList-like object
      const dataTransfer = new DataTransfer();
      images.forEach((img) => dataTransfer.items.add(img.file));
      
      const response = await enrollPerson(name.trim(), info, dataTransfer.files);
      if (response.success) {
        showToast(response.message || 'Person enrolled successfully!', 'success');
        
        if (response.rebuild_started) {
          showToast('Database is syncing...', 'info');
        }
        
        // Cleanup
        images.forEach((img) => URL.revokeObjectURL(img.preview));
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

  const canProceedToStep2 = name.trim().length > 0;
  const canProceedToStep3 = images.length > 0;

  return (
    <div className="enroll-page">
      {/* Header */}
      <div className="enroll-header">
        <div className="header-content">
          <h1>Enroll New Identity</h1>
          <p>Add a new person to the criminal detection database</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="enroll-progress">
        <div className={`progress-step ${currentStep >= 1 ? 'active' : ''} ${currentStep > 1 ? 'completed' : ''}`}>
          <div className="step-number">
            {currentStep > 1 ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
            ) : '1'}
          </div>
          <span className="step-label">Basic Info</span>
        </div>
        <div className="progress-line"></div>
        <div className={`progress-step ${currentStep >= 2 ? 'active' : ''} ${currentStep > 2 ? 'completed' : ''}`}>
          <div className="step-number">
            {currentStep > 2 ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
            ) : '2'}
          </div>
          <span className="step-label">Upload Images</span>
        </div>
        <div className="progress-line"></div>
        <div className={`progress-step ${currentStep >= 3 ? 'active' : ''}`}>
          <div className="step-number">3</div>
          <span className="step-label">Review</span>
        </div>
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit} className="enroll-form">
        {/* Step 1: Basic Info */}
        <div className={`enroll-step ${currentStep === 1 ? 'active' : ''}`}>
          <div className="step-card">
            <div className="step-card-header">
              <div className="step-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
              </div>
              <div>
                <h2>Personal Information</h2>
                <p>Enter the basic details of the person</p>
              </div>
            </div>

            <div className="form-fields">
              <div className="form-field">
                <label htmlFor="name">Full Name *</label>
                <input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter full name"
                  className="input-modern"
                  autoFocus
                />
              </div>

              <div className="form-field">
                <label htmlFor="info">
                  Additional Information
                  <span className="optional-tag">Optional</span>
                </label>
                <textarea
                  id="info"
                  value={info}
                  onChange={(e) => setInfo(e.target.value)}
                  placeholder="Criminal record, identifying marks, known associates, last seen location..."
                  className="textarea-modern"
                  rows={4}
                />
              </div>
            </div>

            <div className="step-actions">
              <button 
                type="button" 
                className="btn-modern primary"
                onClick={() => setCurrentStep(2)}
                disabled={!canProceedToStep2}
              >
                Continue
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Step 2: Upload Images */}
        <div className={`enroll-step ${currentStep === 2 ? 'active' : ''}`}>
          <div className="step-card">
            <div className="step-card-header">
              <div className="step-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
                </svg>
              </div>
              <div>
                <h2>Upload Photos</h2>
                <p>Add clear face photos for better recognition accuracy</p>
              </div>
            </div>

            {/* Drop Zone */}
            <div 
              className={`drop-zone ${isDragging ? 'dragging' : ''} ${images.length > 0 ? 'has-images' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={(e) => handleFiles(e.target.files)}
                style={{ display: 'none' }}
              />
              
              {images.length === 0 ? (
                <div className="drop-zone-content">
                  <div className="drop-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
                    </svg>
                  </div>
                  <p className="drop-text">Drag & drop images here</p>
                  <p className="drop-subtext">or click to browse</p>
                  <span className="drop-hint">Supports: JPG, PNG, BMP</span>
                </div>
              ) : (
                <div className="drop-zone-mini">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                  </svg>
                  <span>Add more images</span>
                </div>
              )}
            </div>

            {/* Image Previews */}
            {images.length > 0 && (
              <div className="image-previews">
                <div className="previews-header">
                  <span>{images.length} image{images.length !== 1 ? 's' : ''} selected</span>
                  <button 
                    type="button" 
                    className="clear-all-btn"
                    onClick={() => {
                      images.forEach((img) => URL.revokeObjectURL(img.preview));
                      setImages([]);
                    }}
                  >
                    Clear all
                  </button>
                </div>
                <div className="previews-grid">
                  {images.map((img, index) => (
                    <div key={index} className="preview-item">
                      <img src={img.preview} alt={`Preview ${index + 1}`} />
                      <button 
                        type="button"
                        className="remove-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeImage(index);
                        }}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                      </button>
                      <span className="preview-name">{img.file.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="step-actions">
              <button 
                type="button" 
                className="btn-modern secondary"
                onClick={() => setCurrentStep(1)}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                </svg>
                Back
              </button>
              <button 
                type="button" 
                className="btn-modern primary"
                onClick={() => setCurrentStep(3)}
                disabled={!canProceedToStep3}
              >
                Continue
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Step 3: Review */}
        <div className={`enroll-step ${currentStep === 3 ? 'active' : ''}`}>
          <div className="step-card">
            <div className="step-card-header">
              <div className="step-icon success">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
              </div>
              <div>
                <h2>Review & Submit</h2>
                <p>Verify the information before enrolling</p>
              </div>
            </div>

            <div className="review-content">
              <div className="review-section">
                <h3>Personal Information</h3>
                <div className="review-item">
                  <span className="review-label">Name</span>
                  <span className="review-value">{name || '—'}</span>
                </div>
                <div className="review-item">
                  <span className="review-label">Additional Info</span>
                  <span className="review-value">{info || 'Not provided'}</span>
                </div>
              </div>

              <div className="review-section">
                <h3>Photos ({images.length})</h3>
                <div className="review-images">
                  {images.map((img, index) => (
                    <img key={index} src={img.preview} alt={`Review ${index + 1}`} />
                  ))}
                </div>
              </div>
            </div>

            <div className="step-actions">
              <button 
                type="button" 
                className="btn-modern secondary"
                onClick={() => setCurrentStep(2)}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                </svg>
                Back
              </button>
              <button 
                type="submit" 
                className="btn-modern success"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <div className="btn-spinner"></div>
                    Enrolling...
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                    Complete Enrollment
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default Enroll;
