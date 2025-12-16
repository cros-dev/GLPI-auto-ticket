/**
 * Interface que representa uma sugestão de categoria retornada pela API
 */
export interface CategorySuggestion {
  id: number;
  suggested_path: string;
  ticket_id: number;
  ticket_title: string;
  ticket_content: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string; // ISO date string
  reviewed_at: string | null; // ISO date string ou null
  reviewed_by: string | null;
  notes: string;
}



