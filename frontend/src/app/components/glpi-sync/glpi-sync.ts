import { ChangeDetectionStrategy, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { finalize } from 'rxjs/operators';
import { ButtonModule } from 'primeng/button';
import { ConfirmationService } from 'primeng/api';

import { ApiService } from '../../services/api.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';

/**
 * Tela de sincronização de categorias do GLPI.
 *
 * Permite disparar manualmente o endpoint do backend que sincroniza
 * as categorias a partir da API do GLPI, atualizando o espelho local.
 */
@Component({
  selector: 'app-glpi-sync',
  standalone: true,
  imports: [CommonModule, ButtonModule],
  templateUrl: './glpi-sync.html',
  styleUrl: './glpi-sync.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class GlpiSyncComponent {
  /** Indica se a sincronização está em andamento. */
  syncing = false;

  /** Resultado mais recente da sincronização (quando disponível). */
  lastResult: { created: number; updated: number; deleted: number; total: number } | null = null;

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService,
    private confirmationService: ConfirmationService
  ) {}

  /**
   * Dispara a sincronização de categorias do GLPI.
   */
  sync(): void {
    if (this.syncing) {
      return;
    }

    this.confirmationService.confirm({
      message: 'Deseja sincronizar as categorias do GLPI agora?',
      header: 'Confirmar Sincronização',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Sim',
      rejectLabel: 'Não',
      accept: () => {
        this.syncing = true;
        this.lastResult = null;

        this.apiService
          .syncGlpiCategoriesFromApi()
          .pipe(finalize(() => (this.syncing = false)))
          .subscribe({
            next: (result) => {
              this.lastResult = result;
              this.notificationService.showSuccess('Sincronização concluída com sucesso!');
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


