/**
 * Utilitários para tradução e formatação de status.
 */

/**
 * Status possíveis para uma sugestão de categoria.
 */
export type CategorySuggestionStatus = 'pending' | 'approved' | 'rejected';

/**
 * Traduz o status da sugestão de categoria para português.
 * 
 * @param status - Status em inglês (pending, approved, rejected)
 * @returns Status traduzido para português
 * 
 * @example
 * ```typescript
 * translateCategorySuggestionStatus('pending'); // 'Pendente'
 * translateCategorySuggestionStatus('approved'); // 'Aprovado'
 * translateCategorySuggestionStatus('rejected'); // 'Rejeitado'
 * ```
 */
export function translateCategorySuggestionStatus(status: CategorySuggestionStatus): string {
  const statusMap: Record<CategorySuggestionStatus, string> = {
    pending: 'Pendente',
    approved: 'Aprovado',
    rejected: 'Rejeitado'
  };
  return statusMap[status] || status;
}

