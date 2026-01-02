/**
 * Interceptor HTTP para autenticação automática.
 * 
 * Adiciona o token de autenticação JWT em todas as requisições para a API
 * e trata erros HTTP (401, 403, conexão, etc.) com notificações adequadas.
 * 
 * Nota: Para SSPR público, este interceptor não adiciona tokens (não há autenticação),
 * mas mantém o tratamento de erros HTTP.
 */
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { NotificationService } from '../services/notification.service';
import { getHttpErrorInfo, HttpErrorType } from '../utils/error-handler.utils';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const notificationService = inject(NotificationService);

  // Para SSPR público, não adicionamos tokens de autenticação
  // As requisições são públicas (password-reset endpoints)

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      const errorInfo = getHttpErrorInfo(error);

      // Tratamento específico para erro 401 (não autorizado)
      if (error.status === 401) {
        notificationService.showError(
          'Erro de autenticação. Verifique suas credenciais.',
          'Erro de Autenticação'
        );
      }
      // Tratamento para erro 403 (proibido)
      else if (error.status === 403) {
        notificationService.showWarning(
          errorInfo.message,
          'Acesso Negado'
        );
      }
      // Tratamento para erros de conexão (backend offline, CORS, etc.)
      else if (errorInfo.type === HttpErrorType.CONNECTION) {
        notificationService.showError(
          errorInfo.message,
          'Erro de Conexão'
        );
      }
      // Para outros erros, o componente que fez a requisição pode tratar
      // mas também exibimos uma notificação genérica se necessário
      // (evitamos duplicar notificações que já são tratadas nos componentes)

      return throwError(() => error);
    })
  );
};

