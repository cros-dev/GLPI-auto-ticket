import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { ConfirmationService } from 'primeng/api';
import { Subject } from 'rxjs';
import { takeUntil, distinctUntilChanged } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { CacheService } from '../../services/cache.service';
import { CategorySuggestion } from '../../models/category-suggestion.interface';
import { formatDate } from '../../utils/date.utils';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';
import { decodeHtmlEntities } from '../../utils/html.utils';
import { translateCategorySuggestionStatus } from '../../utils/status.utils';
import { BreadcrumbComponent, BreadcrumbItem } from '../breadcrumb/breadcrumb';
import { CategorySuggestionsDashboard } from '../category-suggestions-dashboard/category-suggestions-dashboard';
import { LoadingComponent } from '../loading/loading.component';
import { ContentDialogComponent } from '../content-dialog/content-dialog.component';

/**
 * Componente para visualização e aprovação/rejeição de sugestões de categorias.
 * 
 * Exibe uma lista de sugestões de categorias pendentes, permitindo ao usuário
 * aprovar ou rejeitar cada sugestão individualmente.
 */
@Component({
  selector: 'app-category-suggestions',
  imports: [
    CommonModule,
    FormsModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    BreadcrumbComponent,
    CategorySuggestionsDashboard,
    LoadingComponent,
    ContentDialogComponent
  ],
  templateUrl: './category-suggestions.html',
  styleUrl: './category-suggestions.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CategorySuggestions implements OnInit, OnDestroy {
  /** Lista de sugestões de categorias carregadas. */
  suggestions: CategorySuggestion[] = [];
  
  /** Indica se está carregando dados. */
  loading = false;
  
  /** Mensagem de erro, se houver. */
  error: string | null = null;

  /** Status atual para filtrar as sugestões. */
  currentStatus: 'pending' | 'approved' | 'rejected' = 'pending';

  /** Indica se deve exibir o dashboard (quando não há query params de status). */
  showDashboard = false;

  /** Controla a visibilidade do dialog de conteúdo. */
  showContentDialog = false;

  /** Conteúdo atual a ser exibido no dialog. */
  dialogContent: string = '';

  /** Título atual do dialog. */
  dialogTitle: string = 'Conteúdo do Ticket';

  /** Controla a visibilidade do dialog de edição. */
  showEditDialog = false;

  /** Sugestão sendo editada. */
  editingSuggestion: CategorySuggestion | null = null;

  /** Caminho da categoria sendo editado. */
  editingSuggestedPath: string = '';

  /** Notas sendo editadas. */
  editingNotes: string = '';

  /** Indica se está salvando a edição. */
  savingEdit = false;

  /** Subject para gerenciar unsubscribe. */
  private destroy$ = new Subject<void>();

  /** Prefixo usado para as chaves de cache. */
  private readonly cachePrefix = 'category-suggestions';

  /** Indica se está visualizando sugestões aprovadas (sem ações de aprovar/rejeitar). */
  get isApprovedView(): boolean {
    return this.currentStatus === 'approved';
  }

  /** Título da página baseado no status. */
  get pageTitle(): string {
    if (this.currentStatus === 'approved') {
      return 'Sugestões Aprovadas';
    } else if (this.currentStatus === 'rejected') {
      return 'Sugestões Rejeitadas';
    }
    return 'Sugestões de Categorias';
  }

  /** Label do breadcrumb baseado no status. */
  get breadcrumbLabel(): string {
    if (this.currentStatus === 'approved') {
      return 'Aprovadas';
    } else if (this.currentStatus === 'rejected') {
      return 'Rejeitadas';
    }
    return 'Pendentes';
  }

  /** Itens do breadcrumb. */
  get breadcrumbItems(): BreadcrumbItem[] {
    return [
      { label: 'Início', route: '/' },
      { label: 'Sugestões de Categorias', route: '/category-suggestions' },
      { label: 'GLPI' },
      { label: this.breadcrumbLabel }
    ];
  }

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private cacheService: CacheService,
    private confirmationService: ConfirmationService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  /**
   * Inicializa o componente verificando o status da rota e carregando as sugestões.
   */
  ngOnInit(): void {
    // Inicializa baseado na rota atual de forma síncrona
    const status = this.route.snapshot.queryParams['status'] as 'pending' | 'approved' | 'rejected' | undefined;
    
    if (!status) {
      // Se não há status, mostra dashboard
      this.showDashboard = true;
    } else {
      // Se há status, mostra lista
      this.showDashboard = false;
      this.currentStatus = status;
      this.loadSuggestions();
    }
    
    // Se inscreve para mudanças futuras nos query params
    this.route.queryParams.pipe(
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(params => {
      const newStatus = params['status'] as 'pending' | 'approved' | 'rejected' | undefined;
      
      if (!newStatus) {
        // Se não há status, mostra dashboard
        this.showDashboard = true;
        this.currentStatus = 'pending'; // Reset para o padrão
      } else {
        // Se há status, mostra lista
        this.showDashboard = false;
        this.currentStatus = newStatus;
        this.loadSuggestions();
      }
    });
  }

  /**
   * Limpa recursos ao destruir o componente.
   */
  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Carrega a lista de sugestões de categorias da API conforme o status atual.
   * Utiliza cache para evitar requisições desnecessárias.
   * 
   * @param forceRefresh - Se true, força uma nova requisição mesmo que exista cache
   */
  loadSuggestions(forceRefresh: boolean = false): void {
    const cacheKey = `${this.cachePrefix}-${this.currentStatus}`;
    
    // Verifica se existe no cache e não está forçando refresh
    if (!forceRefresh) {
      const cached = this.cacheService.get<CategorySuggestion[]>(cacheKey);
      if (cached) {
        this.suggestions = cached;
        this.loading = false;
        this.error = null;
        this.cdr.markForCheck();
        return;
      }
    }

    this.loading = true;
    this.error = null;
    this.cdr.markForCheck();

    this.apiService.getCategorySuggestions(this.currentStatus).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (data) => {
        // Armazena no cache (sem TTL, cache manual via delete)
        this.cacheService.set(cacheKey, data);
        this.suggestions = data;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.error = errorInfo.message;
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao carregar sugestões:', err);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Aprova uma sugestão de categoria.
   * 
   * @param id - ID da sugestão a ser aprovada
   */
  approveSuggestion(id: number): void {
    this.apiService.approveCategorySuggestion(id).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: () => {
        this.suggestions = this.suggestions.filter(s => s.id !== id);
        // Limpa o cache de pendentes e estatísticas para recarregar na próxima vez
        this.cacheService.delete(`${this.cachePrefix}-pending`);
        this.cacheService.delete('category-suggestions-stats');
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
    this.confirmationService.confirm({
      message: 'Tem certeza que deseja rejeitar esta sugestão?',
      header: 'Confirmar Rejeição',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Sim',
      rejectLabel: 'Não',
      accept: () => {
        this.apiService.rejectCategorySuggestion(id).pipe(
          takeUntil(this.destroy$)
        ).subscribe({
          next: () => {
            this.suggestions = this.suggestions.filter(s => s.id !== id);
            // Limpa o cache de pendentes e estatísticas para recarregar na próxima vez
            this.cacheService.delete(`${this.cachePrefix}-pending`);
            this.cacheService.delete('category-suggestions-stats');
            this.notificationService.showSuccess('Sugestão rejeitada com sucesso!');
          },
          error: (err) => {
            const errorInfo = getHttpErrorInfo(err);
            this.notificationService.showError(errorInfo.message, 'Erro');
            console.error('Erro ao rejeitar:', err);
          }
        });
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


  /**
   * Decodifica entidades HTML escapadas para exibição como texto normal.
   * 
   * @param html - String com entidades HTML escapadas ou null
   * @returns String com caracteres decodificados
   */
  decodeHtml(html: string | null | undefined): string {
    return decodeHtmlEntities(html);
  }

  /**
   * Traduz o status da sugestão para português.
   * 
   * @param status - Status em inglês (pending, approved, rejected)
   * @returns Status traduzido para português
   */
  translateStatus(status: 'pending' | 'approved' | 'rejected'): string {
    return translateCategorySuggestionStatus(status);
  }

  /**
   * Abre o dialog para exibir o conteúdo do ticket.
   * 
   * @param title - Título do ticket
   * @param content - Conteúdo do ticket
   */
  openContentDialog(title: string, content: string | null | undefined): void {
    if (!content) {
      return;
    }
    this.dialogTitle = `Conteúdo: ${decodeHtmlEntities(title)}`;
    this.dialogContent = decodeHtmlEntities(content);
    this.showContentDialog = true;
  }

  /**
   * Abre o dialog para editar uma sugestão de categoria.
   * 
   * @param suggestion - Sugestão a ser editada
   */
  openEditDialog(suggestion: CategorySuggestion): void {
    if (suggestion.status !== 'pending') {
      this.notificationService.showError('Apenas sugestões pendentes podem ser editadas.', 'Erro');
      return;
    }

    this.editingSuggestion = suggestion;
    this.editingSuggestedPath = suggestion.suggested_path;
    this.editingNotes = suggestion.notes || '';
    this.showEditDialog = true;
  }

  /**
   * Fecha o dialog de edição sem salvar.
   */
  closeEditDialog(): void {
    this.showEditDialog = false;
    this.editingSuggestion = null;
    this.editingSuggestedPath = '';
    this.editingNotes = '';
    this.savingEdit = false;
  }

  /**
   * Salva as alterações da sugestão editada.
   */
  saveEdit(): void {
    if (!this.editingSuggestion) {
      return;
    }

    const suggestedPath = this.editingSuggestedPath.trim();
    if (!suggestedPath) {
      this.notificationService.showError('O caminho da categoria é obrigatório.', 'Erro');
      return;
    }

    this.savingEdit = true;

    this.apiService.updateCategorySuggestion(
      this.editingSuggestion.id,
      suggestedPath,
      this.editingNotes.trim() || undefined
    ).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: () => {
        // Atualiza a sugestão na lista local
        const index = this.suggestions.findIndex(s => s.id === this.editingSuggestion!.id);
        if (index !== -1) {
          this.suggestions[index].suggested_path = suggestedPath;
          this.suggestions[index].notes = this.editingNotes.trim();
        }
        
        // Limpa o cache para recarregar na próxima vez
        this.cacheService.delete(`${this.cachePrefix}-${this.currentStatus}`);
        
        this.notificationService.showSuccess('Sugestão atualizada com sucesso!');
        this.closeEditDialog();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.savingEdit = false;
        const errorInfo = getHttpErrorInfo(err);
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao atualizar sugestão:', err);
        this.cdr.markForCheck();
      }
    });
  }
}
