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
 * - ==texto== → <span class="highlight">texto</span> (destaque com cor de fundo)
 * - [Inserir print da tela ...] → <span class="print-instruction">...</span> (instruções de print)
 * - --- → <hr> (linha horizontal)
 * - # Título → <h1>Título</h1>
 * - ## Subtítulo → <h2>Subtítulo</h2>
 * - ### Subsubtítulo → <h3>Subsubtítulo</h3>
 * - #### Subsubtítulo → <h4>Subsubtítulo</h4>
 * - Listas com * ou - (não numeradas)
 * - Listas numeradas (1., 2., etc.)
 * - Listas aninhadas
 * - Quebras de linha
 * 
 * Nota: O conteúdo de itens de lista (<li>) é sempre envolvido em <p> para manter consistência estrutural.
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
  
  // Pilha para gerenciar listas aninhadas: cada elemento é 'ul' ou 'ol'
  const listStack: string[] = [];
  
  const getCurrentIndentLevel = (line: string): number => {
    const match = line.match(/^(\s*)/);
    return match ? Math.floor(match[1].length / 2) : 0;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();
    const indentLevel = getCurrentIndentLevel(line);

    if (trimmedLine.startsWith('* ') || trimmedLine.startsWith('- ')) {
      // Ajusta a pilha de listas baseado no nível de indentação
      while (listStack.length > indentLevel) {
        const lastType = listStack.pop();
        processedLines.push(`</${lastType}>`);
      }
      
      // Se não há lista no nível atual, cria uma
      if (listStack.length === indentLevel) {
        processedLines.push('<ul>');
        listStack.push('ul');
      } else if (listStack.length < indentLevel) {
        // Se o nível é maior que a pilha, preenche com listas vazias (não deveria acontecer, mas trata)
        while (listStack.length < indentLevel) {
          processedLines.push('<ul>');
          listStack.push('ul');
        }
      }
      
      const content = trimmedLine.replace(/^[*\-]\s+/, '').trim();
      const processedContent = processInlineMarkdown(content);
      // Sempre envolve o conteúdo do li em <p>
      processedLines.push(`<li><p>${processedContent}</p></li>`);
      
    } else if (trimmedLine.match(/^\d+\.\s/)) {
      // Ajusta a pilha de listas baseado no nível de indentação
      while (listStack.length > indentLevel) {
        const lastType = listStack.pop();
        processedLines.push(`</${lastType}>`);
      }
      
      // Se não há lista no nível atual, cria uma
      if (listStack.length === indentLevel) {
        processedLines.push('<ol>');
        listStack.push('ol');
      } else if (listStack.length < indentLevel) {
        while (listStack.length < indentLevel) {
          processedLines.push('<ol>');
          listStack.push('ol');
        }
      }
      
      const content = trimmedLine.replace(/^\d+\.\s/, '').trim();
      const processedContent = processInlineMarkdown(content);
      // Sempre envolve o conteúdo do li em <p>
      processedLines.push(`<li><p>${processedContent}</p></li>`);
      
    } else {
      // Fecha todas as listas quando encontramos conteúdo que não é lista
      while (listStack.length > 0) {
        const lastType = listStack.pop();
        processedLines.push(`</${lastType}>`);
      }
      
      if (trimmedLine === '<hr>') {
        processedLines.push('<hr>');
      } else if (trimmedLine === '') {
        processedLines.push('');
      } else if (trimmedLine.startsWith('<h')) {
        processedLines.push(trimmedLine);
      } else if (trimmedLine.startsWith('<img')) {
        // Preserva tags de imagem diretamente
        processedLines.push(trimmedLine);
      } else {
        processedLines.push(`<p>${processInlineMarkdown(trimmedLine)}</p>`);
      }
    }
  }

  // Fecha todas as listas abertas ao final
  while (listStack.length > 0) {
    const lastType = listStack.pop();
    processedLines.push(`</${lastType}>`);
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
  
  // Highlight: ==texto== → <span class="highlight">texto</span>
  // Deve ser processado antes de outros processamentos para evitar conflitos
  result = result.replace(/==([^=]+)==/g, '<span class="highlight">$1</span>');
  
  // Instruções de print: [Inserir print da tela ...]
  result = result.replace(/\[Inserir print da tela ([^\]]+)\]/g, '<span class="print-instruction">Inserir print da tela $1</span>');
  
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  result = result.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  const italicRegex = /(?<!\*)\*([^*\n]+?)\*(?!\*)/g;
  result = result.replace(italicRegex, '<em>$1</em>');
  
  return result;
}

