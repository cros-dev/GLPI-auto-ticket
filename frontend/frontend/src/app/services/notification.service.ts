import { Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';

/**
 * Serviço de notificações da aplicação.
 * 
 * Fornece métodos para exibir notificações toast (sucesso, erro, aviso, info)
 * utilizando o MessageService do PrimeNG. Todas as mensagens são exibidas
 * através do componente p-toast configurado globalmente.
 */
@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  constructor(private messageService: MessageService) {}

  /**
   * Exibe uma mensagem de sucesso.
   * 
   * @param message - Texto da mensagem a ser exibida
   * @param title - Título da notificação (padrão: "Sucesso")
   */
  showSuccess(message: string, title: string = 'Sucesso'): void {
    this.messageService.add({
      severity: 'success',
      summary: title,
      detail: message,
      life: 3000
    });
  }

  /**
   * Exibe uma mensagem de erro.
   * 
   * @param message - Texto da mensagem de erro a ser exibida
   * @param title - Título da notificação (padrão: "Erro")
   */
  showError(message: string, title: string = 'Erro'): void {
    this.messageService.add({
      severity: 'error',
      summary: title,
      detail: message,
      life: 5000
    });
  }

  /**
   * Exibe uma mensagem de aviso.
   * 
   * @param message - Texto da mensagem de aviso a ser exibida
   * @param title - Título da notificação (padrão: "Atenção")
   */
  showWarning(message: string, title: string = 'Atenção'): void {
    this.messageService.add({
      severity: 'warn',
      summary: title,
      detail: message,
      life: 4000
    });
  }

  /**
   * Exibe uma mensagem informativa.
   * 
   * @param message - Texto da mensagem informativa a ser exibida
   * @param title - Título da notificação (padrão: "Informação")
   */
  showInfo(message: string, title: string = 'Informação'): void {
    this.messageService.add({
      severity: 'info',
      summary: title,
      detail: message,
      life: 3000
    });
  }
}

