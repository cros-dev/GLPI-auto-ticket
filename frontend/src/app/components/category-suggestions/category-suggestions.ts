import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { CategorySuggestion } from '../../models/category-suggestion.interface';
import { formatDate } from '../../utils/date.utils';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';

/**
 * Componente para visualização e aprovação/rejeição de sugestões de categorias.
 * 
 * Exibe uma lista de sugestões de categorias pendentes, permitindo ao usuário
 * aprovar ou rejeitar cada sugestão individualmente.
 */
@Component({
  selector: 'app-category-suggestions',
  imports: [CommonModule],
  templateUrl: './category-suggestions.html',
  styleUrl: './category-suggestions.css',
})
export class CategorySuggestions implements OnInit {
  /** Lista de sugestões de categorias carregadas. */
  suggestions: CategorySuggestion[] = [];
  
  /** Indica se está carregando dados. */
  loading = false;
  
  /** Mensagem de erro, se houver. */
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService
  ) {}

  /**
   * Inicializa o componente carregando as sugestões pendentes.
   */
  ngOnInit(): void {
    this.loadSuggestions();
  }

  /**
   * Carrega a lista de sugestões de categorias pendentes da API.
   */
  loadSuggestions(): void {
    this.loading = true;
    this.error = null;

    this.apiService.getCategorySuggestions('pending').subscribe({
      next: (data) => {
        this.suggestions = data;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.error = errorInfo.message;
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao carregar sugestões:', err);
      }
    });
  }

  /**
   * Aprova uma sugestão de categoria.
   * 
   * @param id - ID da sugestão a ser aprovada
   */
  approveSuggestion(id: number): void {
    this.apiService.approveCategorySuggestion(id).subscribe({
      next: () => {
        this.suggestions = this.suggestions.filter(s => s.id !== id);
        this.notificationService.showSuccess('Sugestão aprovada com sucesso!');
      },
      error: (err) => {
        const errorInfo = getHttpErrorInfo(err);
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao aprovar:', err);
      }
    });
  }

  /**
   * Rejeita uma sugestão de categoria após confirmação do usuário.
   * 
   * @param id - ID da sugestão a ser rejeitada
   */
  rejectSuggestion(id: number): void {
    if (!confirm('Tem certeza que deseja rejeitar esta sugestão?')) {
      return;
    }

    this.apiService.rejectCategorySuggestion(id).subscribe({
      next: () => {
        this.suggestions = this.suggestions.filter(s => s.id !== id);
        this.notificationService.showSuccess('Sugestão rejeitada com sucesso!');
      },
      error: (err) => {
        const errorInfo = getHttpErrorInfo(err);
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao rejeitar:', err);
      }
    });
  }

  /**
   * Formata uma data para exibição no formato brasileiro.
   * 
   * @param dateString - String de data no formato ISO ou null
   * @returns Data formatada ou "-" se inválida
   */
  formatDate(dateString: string | null): string {
    return formatDate(dateString);
  }
}
