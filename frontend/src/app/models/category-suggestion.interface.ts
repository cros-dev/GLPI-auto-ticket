/**
 * Interface que representa uma sugestão de categoria retornada pela API.
 */
export interface CategorySuggestion {
  /** ID único da sugestão. */
  id: number;
  
  /** Caminho hierárquico da categoria sugerida (ex: "TI > Requisição > Software"). */
  suggested_path: string;
  
  /** ID do ticket GLPI relacionado. */
  ticket_id: number;
  
  /** Título do ticket GLPI. */
  ticket_title: string;
  
  /** Conteúdo/descrição do ticket GLPI. */
  ticket_content: string;
  
  /** Status atual da sugestão. */
  status: 'pending' | 'approved' | 'rejected';
  
  /** Data de criação da sugestão (formato ISO). */
  created_at: string;
  
  /** Data de revisão da sugestão (formato ISO) ou null se ainda não revisada. */
  reviewed_at: string | null;
  
  /** Nome do usuário que revisou a sugestão ou null. */
  reviewed_by: string | null;
  
  /** Notas adicionais sobre a sugestão. */
  notes: string;
}



