/**
 * Interface que representa as estatísticas de sugestões de categorias.
 */
export interface CategorySuggestionStats {
  /** Total de sugestões. */
  total: number;
  
  /** Quantidade de sugestões pendentes. */
  pending: number;
  
  /** Quantidade de sugestões aprovadas. */
  approved: number;
  
  /** Quantidade de sugestões rejeitadas. */
  rejected: number;
}

