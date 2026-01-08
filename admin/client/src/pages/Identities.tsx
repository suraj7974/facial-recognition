import { useState, useEffect } from 'react';
import { getIdentities, getPerson } from '../services/api';
import type { PersonDetails } from '../types';
import PersonModal from '../components/PersonModal';

interface IdentitiesProps {
  showToast: (message: string, type: 'success' | 'error' | 'warning' | 'info') => void;
}

const Identities = ({ showToast }: IdentitiesProps) => {
  const [identities, setIdentities] = useState<[string, number][]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPerson, setSelectedPerson] = useState<string | null>(null);
  const [personData, setPersonData] = useState<PersonDetails | null>(null);

  useEffect(() => {
    loadIdentities();
  }, []);

  const loadIdentities = async () => {
    setIsLoading(true);
    try {
      const response = await getIdentities();
      const sorted = (response.identities || []).sort((a, b) => a[0].localeCompare(b[0]));
      setIdentities(sorted);
    } catch {
      showToast('Failed to load identities', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePersonClick = async (name: string) => {
    try {
      const data = await getPerson(name);
      setPersonData(data);
      setSelectedPerson(name);
    } catch {
      showToast('Failed to load person details', 'error');
    }
  };

  const handleCloseModal = () => {
    setSelectedPerson(null);
    setPersonData(null);
  };

  const handlePersonDeleted = () => {
    loadIdentities();
  };

  const handleImageAdded = async () => {
    if (selectedPerson) {
      const data = await getPerson(selectedPerson);
      setPersonData(data);
      loadIdentities();
    }
  };

  const filteredIdentities = identities.filter(([name]) =>
    name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div>
      <div className="page-header">
        <h1>Identities</h1>
      </div>

      <div className="search-box">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
        </svg>
        <input
          type="text"
          placeholder="Search by name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      ) : filteredIdentities.length === 0 ? (
        <div className="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
          </svg>
          <p>{searchTerm ? 'No identities found matching your search.' : 'No identities found.'}</p>
        </div>
      ) : (
        <div className="identity-grid">
          {filteredIdentities.map(([name, count]) => (
            <div
              key={name}
              className="identity-card"
              onClick={() => handlePersonClick(name)}
            >
              <h3>{name}</h3>
              <p>{count} image(s)</p>
            </div>
          ))}
        </div>
      )}

      {selectedPerson && (
        <PersonModal
          name={selectedPerson}
          personData={personData}
          onClose={handleCloseModal}
          onPersonDeleted={handlePersonDeleted}
          onImageAdded={handleImageAdded}
          showToast={showToast}
        />
      )}
    </div>
  );
};

export default Identities;
