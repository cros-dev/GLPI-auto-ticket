import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { StepperModule } from 'primeng/stepper';
import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';
import { markdownToHtml } from '../../utils/markdown.utils';
import { BreadcrumbComponent, BreadcrumbItem } from '../breadcrumb/breadcrumb';
import { LoadingComponent } from '../loading/loading.component';
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
    BreadcrumbComponent,
    LoadingComponent
  ],
  templateUrl: './knowledge-base.html',
  styleUrl: './knowledge-base.css'
})
export class KnowledgeBaseComponent {
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

  /** Step atual do stepper (para navegação entre artigos). */
  currentStep = 1;

  /** Itens do breadcrumb. */
  breadcrumbItems: BreadcrumbItem[] = [
    { label: 'Início', route: '/' },
    { label: 'Base de Conhecimento' }
  ];

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer
  ) {}

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

    this.loading = true;
    this.error = null;
    this.articleResult = null;

    const request: KnowledgeBaseArticleRequest = {
      article_type: this.articleType,
      category: categoryTrimmed,
      context: contextTrimmed
    };

    this.apiService.generateKnowledgeBaseArticle(request).subscribe({
      next: (response) => {
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

    // Converte Markdown para HTML
    let htmlContent = markdownToHtml(currentArticle.content);
    
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
      let htmlContent = markdownToHtml(article.content);
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
   * Converte o artigo atual (do step selecionado) Markdown para HTML seguro.
   * 
   * @returns HTML sanitizado do artigo atual
   */
  getArticleHtml(): SafeHtml {
    const content = this.getCurrentArticle();
    if (!content) {
      return '';
    }
    const html = markdownToHtml(content);
    return this.sanitizer.bypassSecurityTrustHtml(html);
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
    const content = this.articleResult.articles[index].content;
    const html = markdownToHtml(content);
    return this.sanitizer.bypassSecurityTrustHtml(html);
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
}

