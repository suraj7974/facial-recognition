import axios from 'axios';
import type { 
  IdentitiesResponse, 
  PersonDetails, 
  ApiResponse, 
  LogResponse, 
  RebuildStatus, 
  StatsResponse 
} from '../types';

export type { PersonDetails } from '../types';

const API_BASE = 'http://localhost:5001';

const api = axios.create({
  baseURL: API_BASE,
});

export const getIdentities = async (): Promise<IdentitiesResponse> => {
  const response = await api.get<IdentitiesResponse>('/api/identities');
  return response.data;
};

export const getPerson = async (name: string): Promise<PersonDetails> => {
  const response = await api.get<PersonDetails>(`/api/person/${encodeURIComponent(name)}`);
  return response.data;
};

export const getImageUrl = (person: string, filename: string): string => {
  return `${API_BASE}/images/${encodeURIComponent(person)}/${encodeURIComponent(filename)}`;
};

export const enrollPerson = async (
  name: string, 
  info: string, 
  images: FileList,
  autoRebuild: boolean = true
): Promise<ApiResponse> => {
  const formData = new FormData();
  formData.append('name', name);
  formData.append('info', info);
  formData.append('auto_rebuild', autoRebuild.toString());
  Array.from(images).forEach((file) => {
    formData.append('images', file);
  });
  const response = await api.post<ApiResponse>('/api/enroll', formData);
  return response.data;
};

export const addImage = async (
  person: string, 
  image: File,
  autoRebuild: boolean = true
): Promise<ApiResponse> => {
  const formData = new FormData();
  formData.append('person', person);
  formData.append('image', image);
  formData.append('auto_rebuild', autoRebuild.toString());
  const response = await api.post<ApiResponse>('/api/add_image', formData);
  return response.data;
};

export const deletePerson = async (
  person: string,
  autoRebuild: boolean = true
): Promise<ApiResponse> => {
  const formData = new FormData();
  formData.append('person', person);
  formData.append('auto_rebuild', autoRebuild.toString());
  const response = await api.post<ApiResponse>('/api/delete_person', formData);
  return response.data;
};

export const deleteImage = async (
  person: string,
  filename: string,
  autoRebuild: boolean = true
): Promise<ApiResponse> => {
  const formData = new FormData();
  formData.append('person', person);
  formData.append('filename', filename);
  formData.append('auto_rebuild', autoRebuild.toString());
  const response = await api.post<ApiResponse>('/api/delete_image', formData);
  return response.data;
};

export const rebuildDatabase = async (): Promise<ApiResponse & { status?: RebuildStatus }> => {
  const response = await api.post<ApiResponse & { status?: RebuildStatus }>('/api/rebuild_db');
  return response.data;
};

export const getRebuildStatus = async (): Promise<RebuildStatus> => {
  const response = await api.get<RebuildStatus>('/api/rebuild_status');
  return response.data;
};

export const getStats = async (): Promise<StatsResponse> => {
  const response = await api.get<StatsResponse>('/api/stats');
  return response.data;
};

export const getLatestLog = async (): Promise<LogResponse> => {
  const response = await api.get<LogResponse>('/api/latest_log');
  return response.data;
};
