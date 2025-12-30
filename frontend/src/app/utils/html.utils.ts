/**
 * Utilitários para manipulação de HTML e texto.
 */

/**
 * Decodifica entidades HTML escapadas para caracteres normais.
 * 
 * Converte entidades como &lt; para <, &gt; para >, &amp; para &, etc.
 * Útil quando o backend retorna conteúdo HTML escapado que precisa ser exibido
 * como texto normal.
 * 
 * @param html - String com entidades HTML escapadas
 * @returns String com caracteres decodificados
 * 
 * @example
 * ```typescript
 * decodeHtmlEntities('&lt;selecao@redeamazonica.com.br&gt;'); // '<selecao@redeamazonica.com.br>'
 * decodeHtmlEntities('Texto &amp; mais texto'); // 'Texto & mais texto'
 * ```
 */
export function decodeHtmlEntities(html: string | null | undefined): string {
  if (!html) {
    return '';
  }

  // Usa um elemento textarea temporário para decodificar as entidades HTML
  // Esta é uma abordagem segura que funciona com todas as entidades HTML
  const textarea = document.createElement('textarea');
  textarea.innerHTML = html;
  return textarea.value;
}

