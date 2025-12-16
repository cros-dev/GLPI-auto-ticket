import { Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  constructor(private messageService: MessageService) {}

  /**
   * Mostra mensagem de sucesso
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
   * Mostra mensagem de erro
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
   * Mostra mensagem de aviso
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
   * Mostra mensagem informativa
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



