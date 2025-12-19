import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';
import { BreadcrumbComponent, BreadcrumbItem } from '../breadcrumb/breadcrumb';
import { LoadingComponent } from '../loading/loading.component';

/**
 * Componente para preview de sugestão de categoria.
 * 
 * Permite testar e validar sugestões de categorias antes de criar tickets ou categorias no GLPI.
 * Envia título e conteúdo para a IA e retorna uma prévia da categoria sugerida.
 */
@Component({
  selector: 'app-category-preview',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    InputTextModule,
    BreadcrumbComponent,
    LoadingComponent
  ],
  templateUrl: './category-preview.html',
  styleUrl: './category-preview.css'
})
export class CategoryPreviewComponent {
  /** Título do ticket sendo testado. */
  title: string = '';

  /** Conteúdo do ticket sendo testado. */
  content: string = '';

  /** Indica se está gerando preview. */
  loading = false;

  /** Resultado do preview (quando disponível). */
  previewResult: {
    suggested_path: string;
    suggested_category_id?: number;
    ticket_type?: number;
    ticket_type_label?: string;
    classification_method: 'existing_category' | 'new_suggestion';
    confidence?: string;
    note: string;
  } | null = null;

  /** Mensagem de erro, se houver. */
  error: string | null = null;

  /** Itens do breadcrumb. */
  breadcrumbItems: BreadcrumbItem[] = [
    { label: 'Início', route: '/' },
    { label: 'Preview de Categoria' }
  ];

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private cdr: ChangeDetectorRef
  ) {}

  /**
   * Gera preview da sugestão de categoria.
   */
  generatePreview(): void {
    const titleTrimmed = this.title.trim();
    const contentTrimmed = this.content.trim();

    if (!titleTrimmed) {
      this.notificationService.showError('O título é obrigatório.', 'Erro');
      return;
    }

    this.loading = true;
    this.error = null;
    this.previewResult = null;

    this.apiService.previewCategorySuggestion(titleTrimmed, contentTrimmed).subscribe({
      next: (result) => {
        this.previewResult = result;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.error = errorInfo.message;
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao gerar preview:', err);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Limpa o formulário e resultados.
   */
  clear(): void {
    this.title = '';
    this.content = '';
    this.previewResult = null;
    this.error = null;
  }

  /**
   * Traduz o método de classificação para português.
   */
  translateClassificationMethod(method: 'existing_category' | 'new_suggestion'): string {
    if (method === 'existing_category') {
      return 'Categoria Existente';
    }
    return 'Nova Sugestão';
  }

  /**
   * Traduz o tipo de ticket para português.
   */
  translateTicketType(type?: number): string {
    if (type === 1) {
      return 'Incidente';
    }
    if (type === 2) {
      return 'Requisição';
    }
    return '-';
  }

  /**
   * Traduz o nível de confiança para português.
   */
  translateConfidence(confidence?: string): string {
    if (confidence === 'high') {
      return 'Alta';
    }
    if (confidence === 'medium') {
      return 'Média';
    }
    if (confidence === 'low') {
      return 'Baixa';
    }
    return '-';
  }
}

