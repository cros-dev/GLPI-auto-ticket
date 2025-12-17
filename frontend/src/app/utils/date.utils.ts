/**
 * Utilitários para formatação e manipulação de datas.
 */

/**
 * Formata uma string de data ISO para o formato brasileiro.
 * 
 * @param dateString - String de data no formato ISO (ex: "2025-12-16T10:30:00Z") ou null
 * @returns String formatada no padrão brasileiro (ex: "16/12/2025, 10:30:00") ou "-" se inválida
 * 
 * @example
 * ```typescript
 * formatDate('2025-12-16T10:30:00Z'); // "16/12/2025, 10:30:00"
 * formatDate(null); // "-"
 * ```
 */
export function formatDate(dateString: string | null): string {
  if (!dateString) {
    return '-';
  }
  
  try {
    return new Date(dateString).toLocaleString('pt-BR');
  } catch (error) {
    console.error('Erro ao formatar data:', error);
    return '-';
  }
}

/**
 * Formata apenas a data (sem hora) para o formato brasileiro.
 * 
 * @param dateString - String de data no formato ISO ou null
 * @returns String formatada apenas com data (ex: "16/12/2025") ou "-" se inválida
 * 
 * @example
 * ```typescript
 * formatDateOnly('2025-12-16T10:30:00Z'); // "16/12/2025"
 * ```
 */
export function formatDateOnly(dateString: string | null): string {
  if (!dateString) {
    return '-';
  }
  
  try {
    return new Date(dateString).toLocaleDateString('pt-BR');
  } catch (error) {
    console.error('Erro ao formatar data:', error);
    return '-';
  }
}

