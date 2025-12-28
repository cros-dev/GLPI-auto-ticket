import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { finalize } from 'rxjs/operators';
import { ButtonModule } from 'primeng/button';
import { ConfirmationService } from 'primeng/api';

import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';
import { BreadcrumbComponent, BreadcrumbItem } from '../breadcrumb/breadcrumb';

/**
 * Tela de sincronização de categorias do GLPI.
 *
 * Permite disparar manualmente o endpoint do backend que sincroniza
 * as categorias a partir da API do GLPI, atualizando o espelho local.
 */
@Component({
  selector: 'app-glpi-sync',
  standalone: true,
  imports: [CommonModule, ButtonModule, BreadcrumbComponent],
  templateUrl: './glpi-sync.html',
  styleUrl: './glpi-sync.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class GlpiSyncComponent {
  /** Indica se a sincronização está em andamento. */
  loading = false;

  /** Resultado mais recente da sincronização (quando disponível). */
  lastResult: { created: number; updated: number; deleted: number; total: number } | null = null;

  /** Itens do breadcrumb. */
  breadcrumbItems: BreadcrumbItem[] = [
    { label: 'Início', route: '/' },
    { label: 'Integração' },
    { label: 'GLPI' },
    { label: 'Sincronizar Categorias' }
  ];

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private confirmationService: ConfirmationService,
    private cdr: ChangeDetectorRef
  ) {}

  /**
   * Dispara a sincronização de categorias do GLPI.
   */
  sync(): void {
    if (this.loading) {
      return;
    }

    this.confirmationService.confirm({
      message: 'Deseja sincronizar as categorias do GLPI agora?',
      header: 'Confirmar Sincronização de Categorias',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Sim',
      rejectLabel: 'Não',
      accept: () => {
        this.loading = true;
        this.lastResult = null;
        this.cdr.markForCheck();

        this.apiService
          .syncGlpiCategoriesFromApi()
          .pipe(finalize(() => {
            this.loading = false;
            this.cdr.markForCheck();
          }))
          .subscribe({
            next: (result) => {
              this.lastResult = result;
              this.cdr.markForCheck();
              this.notificationService.showSuccess('Sincronização de categorias concluída com sucesso!');
            },
            error: (err) => {
              const errorInfo = getHttpErrorInfo(err);
              this.notificationService.showError(errorInfo.message, 'Erro');
              console.error('Erro ao sincronizar categorias:', err);
            }
          });
      }
    });
  }
}


