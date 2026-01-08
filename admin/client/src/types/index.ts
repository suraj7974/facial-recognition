export interface Identity {
  name: string;
  count: number;
}

export interface PersonDetails {
  images: string[];
  info: string;
}

export interface ApiResponse {
  success: boolean;
  message?: string;
  error?: string;
  rebuild_started?: boolean;
  rebuild_message?: string;
}

export interface IdentitiesResponse {
  identities: [string, number][];
}

export interface LogResponse {
  content: string;
  filename?: string;
}

export interface RebuildStatus {
  is_rebuilding: boolean;
  progress: number;
  status: 'idle' | 'rebuilding' | 'reloading' | 'completed' | 'failed';
  message: string;
  started_at: string | null;
  completed_at: string | null;
  last_error: string | null;
  triggered_by: 'enroll' | 'delete' | 'add_image' | 'delete_image' | 'manual' | null;
}

export interface DatabaseInfo {
  exists: boolean;
  size: number;
  modified: string | null;
}

export interface StatsResponse {
  total_identities: number;
  total_images: number;
  database: DatabaseInfo;
  rebuild_status: RebuildStatus;
}
