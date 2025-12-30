import { Component, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { StepperModule } from 'primeng/stepper';
import { SelectModule } from 'primeng/select';
import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';
import { BreadcrumbComponent, BreadcrumbItem } from '../breadcrumb/breadcrumb';
import { ContentDialogComponent } from '../content-dialog/content-dialog.component';
import { KnowledgeBaseArticleRequest, KnowledgeBaseArticleResponse } from '../../models/knowledge-base-article.interface';

/**
 * Componente para geração de artigos de Base de Conhecimento.
 * 
 * Permite gerar artigos de Base de Conhecimento usando Google Gemini AI,
 * com suporte para três tipos: conceitual, operacional e troubleshooting.
 */
@Component({
  selector: 'app-knowledge-base',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    InputTextModule,
    DialogModule,
    StepperModule,
    SelectModule,
    BreadcrumbComponent,
    ContentDialogComponent
  ],
  templateUrl: './knowledge-base.html',
  styleUrl: './knowledge-base.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class KnowledgeBaseComponent {
  /** Opções de tipo de artigo para o dropdown. */
  articleTypeOptions = [
    { label: 'Conceitual', value: 'conceitual' },
    { label: 'Operacional', value: 'operacional' },
    { label: 'Troubleshooting', value: 'troubleshooting' }
  ];

  /** Tipo do artigo selecionado. */
  articleType: 'conceitual' | 'operacional' | 'troubleshooting' | null = null;

  /** Categoria da Base de Conhecimento. */
  category: string = '';

  /** Contexto do ambiente, sistemas, servidores, softwares envolvidos. */
  context: string = '';

  /** Indica se está gerando artigo. */
  loading = false;

  /** Artigo gerado (quando disponível). */
  articleResult: KnowledgeBaseArticleResponse | null = null;

  /** Mensagem de erro, se houver. */
  error: string | null = null;

  /** Controla a visibilidade do dialog de ajuda sobre tipos de artigo. */
  showHelpDialog = false;

  /** Controla a visibilidade do dialog de ajuda sobre categoria. */
  showCategoryHelpDialog = false;

  /** Controla a visibilidade do dialog de ajuda sobre contexto. */
  showContextHelpDialog = false;

  /** Controla a visibilidade do dialog de resultados (artigos gerados). */
  showResultsDialog = false;

  /** Controla a visibilidade do dialog de conteúdo do artigo. */
  showContentDialog = false;

  /** Título do dialog de conteúdo. */
  contentDialogTitle = '';

  /** Conteúdo HTML do artigo para exibir no dialog. */
  contentDialogHtml: string | null = null;

  /** Índice do artigo atual no dialog de conteúdo. */
  contentDialogArticleIndex: number | null = null;

  /** Step atual do stepper (para navegação entre artigos). */
  currentStep = 1;

  /** Últimos dados usados para gerar artigo (para evitar geração duplicada). */
  private lastGeneratedData: { articleType: string | null; category: string; context: string } | null = null;

  /** Itens do breadcrumb. */
  breadcrumbItems: BreadcrumbItem[] = [
    { label: 'Início', route: '/' },
    { label: 'IA' },
    { label: 'GLPI' },
    { label: 'Base de Conhecimento' },
    { label: 'Gerador de Artigos' }
  ];

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer
  ) {}

  /**
   * Verifica se os dados do formulário mudaram desde a última geração.
   */
  hasDataChanged(): boolean {
    if (!this.lastGeneratedData) {
      return true; // Se nunca gerou, considera como mudado
    }

    const currentData = {
      articleType: this.articleType,
      category: this.category.trim(),
      context: this.context.trim()
    };

    return (
      currentData.articleType !== this.lastGeneratedData.articleType ||
      currentData.category !== this.lastGeneratedData.category ||
      currentData.context !== this.lastGeneratedData.context
    );
  }

  /**
   * Gera artigo de Base de Conhecimento.
   */
  generateArticle(): void {
    if (!this.articleType) {
      this.notificationService.showError('Selecione o tipo do artigo.', 'Erro');
      return;
    }

    const categoryTrimmed = this.category.trim();
    const contextTrimmed = this.context.trim();

    if (!categoryTrimmed) {
      this.notificationService.showError('A categoria é obrigatória.', 'Erro');
      return;
    }

    if (!contextTrimmed) {
      this.notificationService.showError('O contexto é obrigatório.', 'Erro');
      return;
    }

    // Verifica se os dados mudaram
    if (!this.hasDataChanged()) {
      this.notificationService.showWarning('Os dados não foram alterados. Modifique o tipo, categoria ou contexto antes de gerar novamente.', 'Atenção');
      return;
    }

    this.loading = true;
    this.error = null;
    this.articleResult = null;
    this.cdr.markForCheck();

    const request: KnowledgeBaseArticleRequest = {
      article_type: this.articleType,
      category: categoryTrimmed,
      context: contextTrimmed
    };

    this.apiService.generateKnowledgeBaseArticle(request).subscribe({
      next: (response) => {
        // Salva os dados usados para comparação futura
        this.lastGeneratedData = {
          articleType: this.articleType,
          category: categoryTrimmed,
          context: contextTrimmed
        };

        this.articleResult = response;
        this.currentStep = 1; // Reseta para o primeiro artigo
        this.loading = false;
        const articleCount = response.articles.length;
        const message = articleCount > 1 
          ? `${articleCount} artigos gerados com sucesso!`
          : 'Artigo gerado com sucesso!';
        this.notificationService.showSuccess(message, 'Sucesso');
        this.showResultsDialog = true; // Abre o dialog com os resultados
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.error = errorInfo.message;
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao gerar artigo:', err);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Limpa o formulário e resultados.
   */
  clear(): void {
    this.articleType = null;
    this.category = '';
    this.context = '';
    this.articleResult = null;
    this.error = null;
    this.currentStep = 1;
    this.showResultsDialog = false;
    this.lastGeneratedData = null; // Limpa também os dados da última geração
  }

  /**
   * Abre o dialog de resultados.
   */
  openResultsDialog(): void {
    this.showResultsDialog = true;
  }

  /**
   * Fecha o dialog de resultados.
   */
  closeResultsDialog(): void {
    this.showResultsDialog = false;
  }

  /**
   * Copia um artigo específico em formato HTML para a área de transferência.
   * O HTML pode ser colado diretamente no GLPI mantendo toda a formatação.
   * Converte classes CSS para estilos inline para garantir compatibilidade.
   * 
   * @param articleIndex - Índice do artigo a ser copiado (0-based). Se não informado, usa o artigo atual do step.
   */
  copyArticle(articleIndex?: number): void {
    if (!this.articleResult?.articles || this.articleResult.articles.length === 0) {
      return;
    }

    const index = articleIndex !== undefined ? articleIndex : this.currentStep - 1;
    const currentArticle = this.articleResult.articles[index];
    if (!currentArticle) {
      return;
    }

    // Usa HTML já convertido pelo backend
    let htmlContent = currentArticle.content_html || '';
    
    // Converte classes CSS para estilos inline (necessário para o GLPI)
    // Highlight: class="highlight" → style="color: #000000; background-color: #f1c40f;"
    htmlContent = htmlContent.replace(
      /<span class="highlight">/g,
      '<span style="color: #000000; background-color: #f1c40f;">'
    );
    
    // Remove outras classes que não são necessárias no GLPI
    // (instruções de print podem ficar sem estilo, já que são apenas texto)
    htmlContent = htmlContent.replace(/ class="print-instruction"/g, '');
    
    // Copia o HTML formatado para a área de transferência
    navigator.clipboard.writeText(htmlContent).then(() => {
      this.notificationService.showSuccess('Artigo HTML copiado! Cole no GLPI para preservar a formatação.', 'Sucesso');
    }).catch(() => {
      this.notificationService.showError('Erro ao copiar artigo.', 'Erro');
    });
  }

  /**
   * Copia todos os artigos em formato HTML para a área de transferência.
   * Útil quando há múltiplos artigos e o usuário quer copiar tudo de uma vez.
   * Converte classes CSS para estilos inline para garantir compatibilidade com o GLPI.
   */
  copyAllArticles(): void {
    if (!this.articleResult?.articles || this.articleResult.articles.length === 0) {
      return;
    }

    const allArticlesHtml = this.articleResult.articles.map(article => {
      // Usa HTML já convertido pelo backend
      let htmlContent = article.content_html || '';
      htmlContent = htmlContent.replace(
        /<span class="highlight">/g,
        '<span style="color: #000000; background-color: #f1c40f;">'
      );
      htmlContent = htmlContent.replace(/ class="print-instruction"/g, '');
      return htmlContent;
    }).join('\n\n');

    navigator.clipboard.writeText(allArticlesHtml).then(() => {
      const count = this.articleResult!.articles.length;
      this.notificationService.showSuccess(
        `${count} artigo(s) HTML copiado(s)! Cole no GLPI para preservar a formatação.`,
        'Sucesso'
      );
    }).catch(() => {
      this.notificationService.showError('Erro ao copiar artigos.', 'Erro');
    });
  }

  /**
   * Traduz o tipo de artigo para português.
   * 
   * @param type - Tipo do artigo em inglês ('conceitual', 'operacional', 'troubleshooting')
   * @returns Tipo traduzido para português
   */
  translateArticleType(type: string): string {
    const translations: Record<string, string> = {
      'conceitual': 'Conceitual',
      'operacional': 'Operacional',
      'troubleshooting': 'Troubleshooting'
    };
    return translations[type] || type;
  }

  /**
   * Obtém o artigo atual (baseado no step selecionado).
   * 
   * @returns Conteúdo do artigo atual em formato Markdown, ou string vazia se não houver
   */
  getCurrentArticle(): string {
    if (!this.articleResult?.articles || this.articleResult.articles.length === 0) {
      return '';
    }
    const currentArticle = this.articleResult.articles[this.currentStep - 1];
    return currentArticle?.content || '';
  }

  /**
   * Obtém o HTML do artigo atual (do step selecionado).
   * 
   * @returns HTML sanitizado do artigo atual
   */
  getArticleHtml(): SafeHtml {
    if (!this.articleResult?.articles || this.articleResult.articles.length === 0) {
      return '';
    }
    const currentArticle = this.articleResult.articles[this.currentStep - 1];
    if (!currentArticle?.content_html) {
      return '';
    }
    return this.sanitizer.bypassSecurityTrustHtml(currentArticle.content_html);
  }

  /**
   * Extrai o título de um artigo do conteúdo Markdown.
   * Procura pelo padrão "**Base de Conhecimento — [Título]**".
   * 
   * @param content - Conteúdo Markdown do artigo
   * @returns Título extraído ou "Artigo" se não encontrar
   */
  extractArticleTitle(content: string): string {
    const match = content.match(/\*\*Base de Conhecimento — ([^*]+)\*\*/);
    if (match && match[1]) {
      return match[1].trim();
    }
    return 'Artigo';
  }

  /**
   * Obtém a lista de artigos formatados para o stepper.
   * 
   * @returns Array de objetos com título extraído e conteúdo de cada artigo
   */
  getArticles(): Array<{ title: string; content: string }> {
    if (!this.articleResult?.articles) {
      return [];
    }
    return this.articleResult.articles.map(article => ({
      title: this.extractArticleTitle(article.content),
      content: article.content
    }));
  }

  /**
   * Obtém o conteúdo HTML do artigo no índice especificado.
   * 
   * @param index - Índice do artigo (0-based)
   * @returns HTML sanitizado do artigo, ou string vazia se o índice for inválido
   */
  getArticleHtmlByIndex(index: number): SafeHtml {
    if (!this.articleResult?.articles || index < 0 || index >= this.articleResult.articles.length) {
      return '';
    }
    const article = this.articleResult.articles[index];
    if (!article?.content_html) {
      return '';
    }
    return this.sanitizer.bypassSecurityTrustHtml(article.content_html);
  }

  /**
   * Abre o dialog de ajuda sobre tipos de artigo.
   */
  openHelpDialog(): void {
    this.showHelpDialog = true;
  }

  /**
   * Fecha o dialog de ajuda.
   */
  closeHelpDialog(): void {
    this.showHelpDialog = false;
  }

  /**
   * Abre o dialog de ajuda sobre categoria.
   */
  openCategoryHelpDialog(): void {
    this.showCategoryHelpDialog = true;
  }

  /**
   * Fecha o dialog de ajuda sobre categoria.
   */
  closeCategoryHelpDialog(): void {
    this.showCategoryHelpDialog = false;
  }

  /**
   * Abre o dialog de ajuda sobre contexto.
   */
  openContextHelpDialog(): void {
    this.showContextHelpDialog = true;
  }

  /**
   * Fecha o dialog de ajuda sobre contexto.
   */
  closeContextHelpDialog(): void {
    this.showContextHelpDialog = false;
  }

  /**
   * Abre o dialog de conteúdo do artigo.
   * 
   * @param title - Título do artigo
   * @param articleIndex - Índice do artigo (0-based)
   */
  openContentDialog(title: string, articleIndex: number): void {
    if (!this.articleResult?.articles || articleIndex < 0 || articleIndex >= this.articleResult.articles.length) {
      return;
    }
    const article = this.articleResult.articles[articleIndex];
    this.contentDialogTitle = title;
    // Usa HTML já convertido pelo backend
    this.contentDialogHtml = article.content_html || '';
    this.contentDialogArticleIndex = articleIndex;
    this.showContentDialog = true;
  }

  /**
   * Copia o artigo do dialog de conteúdo.
   */
  copyArticleFromDialog(): void {
    if (this.contentDialogArticleIndex !== null) {
      this.copyArticle(this.contentDialogArticleIndex);
    }
  }

  /**
   * Fecha o dialog de conteúdo do artigo.
   */
  closeContentDialog(): void {
    this.showContentDialog = false;
    this.contentDialogHtml = null;
    this.contentDialogArticleIndex = null;
  }
}

