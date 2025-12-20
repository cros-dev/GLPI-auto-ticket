import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
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
        this.loading = false;
        this.notificationService.showSuccess('Artigo gerado com sucesso!', 'Sucesso');
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
  }

  /**
   * Copia o artigo gerado para a área de transferência.
   */
  copyArticle(): void {
    if (!this.articleResult?.article) {
      return;
    }

    navigator.clipboard.writeText(this.articleResult.article).then(() => {
      this.notificationService.showSuccess('Artigo copiado para a área de transferência!', 'Sucesso');
    }).catch(() => {
      this.notificationService.showError('Erro ao copiar artigo.', 'Erro');
    });
  }

  /**
   * Traduz o tipo de artigo para português.
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
   * Converte o artigo Markdown para HTML seguro.
   */
  getArticleHtml(): SafeHtml {
    if (!this.articleResult?.article) {
      return '';
    }
    const html = markdownToHtml(this.articleResult.article);
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}

