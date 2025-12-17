import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { CacheService } from '../../services/cache.service';
import { CategorySuggestionStats } from '../../models/category-suggestion-stats.interface';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';
import { BreadcrumbComponent, BreadcrumbItem } from '../breadcrumb/breadcrumb';
import { LoadingComponent } from '../loading/loading.component';

/**
 * Interface para os cards do dashboard.
 */
interface DashboardCard {
  title: string;
  count: number;
  status: 'pending' | 'approved' | 'rejected' | 'total';
  route: string[];
  queryParams?: { [key: string]: string };
  icon: string;
  color: string;
}

/**
 * Componente de dashboard para visualizar estatísticas de sugestões de categorias.
 * 
 * Exibe cards com contagens por status (pendentes, aprovadas, rejeitadas) e total,
 * permitindo navegação rápida para cada lista.
 */
@Component({
  selector: 'app-category-suggestions-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, ButtonModule, BreadcrumbComponent, LoadingComponent],
  templateUrl: './category-suggestions-dashboard.html',
  styleUrl: './category-suggestions-dashboard.css'
})
export class CategorySuggestionsDashboard implements OnInit, OnDestroy {
  /** Estatísticas carregadas. */
  stats: CategorySuggestionStats | null = null;
  
  /** Indica se está carregando dados. */
  loading = false;
  
  /** Mensagem de erro, se houver. */
  error: string | null = null;

  /** Cards do dashboard. */
  cards: DashboardCard[] = [];

  /** Subject para gerenciar unsubscribe. */
  private destroy$ = new Subject<void>();

  /** Itens do breadcrumb. */
  breadcrumbItems: BreadcrumbItem[] = [
    { label: 'Início', route: '/' },
    { label: 'Sugestões de Categorias' }
  ];

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private cacheService: CacheService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  /**
   * Inicializa o componente carregando as estatísticas.
   */
  ngOnInit(): void {
    this.loadStats();
  }

  /**
   * Carrega as estatísticas das sugestões de categorias.
   */
  loadStats(): void {
    const cacheKey = 'category-suggestions-stats';
    
    // Verifica cache primeiro
    const cached = this.cacheService.get<CategorySuggestionStats>(cacheKey);
    if (cached) {
      this.stats = cached;
      this.loading = false;
      this.error = null;
      this.updateCards();
      this.cdr.markForCheck();
      return;
    }

    this.loading = true;
    this.error = null;
    this.stats = null; // Garante que stats está null enquanto carrega

    this.apiService.getCategorySuggestionStats().pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (data) => {
        this.stats = data;
        // Cacheia por 30 segundos
        this.cacheService.set(cacheKey, data, { ttl: 30000 });
        this.updateCards();
        this.loading = false;
        this.error = null;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.stats = null;
        const errorInfo = getHttpErrorInfo(err);
        this.error = errorInfo.message;
        this.notificationService.showError(errorInfo.message, 'Erro');
        console.error('Erro ao carregar estatísticas:', err);
        this.cdr.markForCheck();
      }
    });
  }

  /**
   * Atualiza os cards do dashboard com as estatísticas carregadas.
   */
  private updateCards(): void {
    if (!this.stats) {
      return;
    }

    this.cards = [
      {
        title: 'Total',
        count: this.stats.total,
        status: 'total',
        route: ['/category-suggestions'],
        queryParams: {},
        icon: 'pi pi-chart-bar',
        color: 'primary'
      },
      {
        title: 'Pendentes',
        count: this.stats.pending,
        status: 'pending',
        route: ['/category-suggestions'],
        queryParams: { status: 'pending' },
        icon: 'pi pi-clock',
        color: 'warning'
      },
      {
        title: 'Aprovadas',
        count: this.stats.approved,
        status: 'approved',
        route: ['/category-suggestions'],
        queryParams: { status: 'approved' },
        icon: 'pi pi-check-circle',
        color: 'success'
      },
      {
        title: 'Rejeitadas',
        count: this.stats.rejected,
        status: 'rejected',
        route: ['/category-suggestions'],
        queryParams: { status: 'rejected' },
        icon: 'pi pi-times-circle',
        color: 'danger'
      }
    ];
  }

  /**
   * Limpa recursos ao destruir o componente.
   */
  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Navega para a rota do card clicado.
   * 
   * @param card - Card clicado
   */
  navigateToCard(card: DashboardCard): void {
    if (card.queryParams) {
      this.router.navigate(card.route, { queryParams: card.queryParams });
    } else {
      this.router.navigate(card.route);
    }
  }
}

