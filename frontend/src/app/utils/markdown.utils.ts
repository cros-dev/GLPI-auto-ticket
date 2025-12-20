/**
 * Utilitários para conversão de Markdown básico para HTML.
 */

/**
 * Converte Markdown básico para HTML.
 * 
 * Suporta:
 * - **texto** → <strong>texto</strong> (negrito)
 * - *texto* → <em>texto</em> (itálico) - apenas quando não for lista
 * - `texto` → <code>texto</code> (código inline)
 * - --- → <hr> (linha horizontal)
 * - # Título → <h1>Título</h1>
 * - ## Subtítulo → <h2>Subtítulo</h2>
 * - ### Subsubtítulo → <h3>Subsubtítulo</h3>
 * - #### Subsubtítulo → <h4>Subsubtítulo</h4>
 * - Listas com * ou - (não numeradas)
 * - Listas numeradas (1., 2., etc.)
 * - Quebras de linha
 * 
 * @param markdown - Texto em Markdown
 * @returns HTML convertido
 */
export function markdownToHtml(markdown: string | null | undefined): string {
  if (!markdown) {
    return '';
  }

  let html = markdown;

  html = html.replace(/^---$/gm, '<hr>');

  html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  const lines = html.split('\n');
  const processedLines: string[] = [];
  let inList = false;
  let inOrderedList = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();

    if (trimmedLine.startsWith('* ')) {
      if (!inList) {
        if (inOrderedList) {
          processedLines.push('</ol>');
          inOrderedList = false;
        }
        processedLines.push('<ul>');
        inList = true;
      }
      const content = trimmedLine.substring(2).trim();
      processedLines.push(`<li>${processInlineMarkdown(content)}</li>`);
    } else if (trimmedLine.match(/^\d+\.\s/)) {
      if (!inOrderedList) {
        if (inList) {
          processedLines.push('</ul>');
          inList = false;
        }
        processedLines.push('<ol>');
        inOrderedList = true;
      }
      const content = trimmedLine.replace(/^\d+\.\s/, '').trim();
      processedLines.push(`<li>${processInlineMarkdown(content)}</li>`);
    } else {
      if (inList) {
        processedLines.push('</ul>');
        inList = false;
      }
      if (inOrderedList) {
        processedLines.push('</ol>');
        inOrderedList = false;
      }
      
      if (trimmedLine === '<hr>') {
        processedLines.push('<hr>');
      } else if (trimmedLine === '') {
        processedLines.push('');
      } else if (trimmedLine.startsWith('<h')) {
        processedLines.push(trimmedLine);
      } else {
        processedLines.push(`<p>${processInlineMarkdown(trimmedLine)}</p>`);
      }
    }
  }

  if (inList) {
    processedLines.push('</ul>');
  }
  if (inOrderedList) {
    processedLines.push('</ol>');
  }

  html = processedLines.join('\n');
  
  html = html.replace(/\n\n+/g, '\n');
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p><h([1-6])>/g, '<h$1>');
  html = html.replace(/<\/h([1-6])><\/p>/g, '</h$1>');
  html = html.replace(/<p><hr><\/p>/g, '<hr>');
  
  return html.trim();
}

/**
 * Processa formatação inline de Markdown (negrito, itálico, código).
 * 
 * @param text - Texto a ser processado
 * @returns Texto com HTML inline
 */
function processInlineMarkdown(text: string): string {
  let result = text;
  
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  result = result.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  const italicRegex = /(?<!\*)\*([^*\n]+?)\*(?!\*)/g;
  result = result.replace(italicRegex, '<em>$1</em>');
  
  return result;
}

