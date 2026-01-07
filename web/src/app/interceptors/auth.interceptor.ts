/**
 * Interceptor HTTP para autenticação automática.
 * 
 * Adiciona o token de autenticação em todas as requisições para a API
 * e trata erros HTTP (401, 403, conexão, etc.) com notificações adequadas.
 * 
 * @param req - Requisição HTTP interceptada
 * @param next - Handler para continuar o fluxo da requisição
 * @returns Observable com a resposta da requisição ou erro
 */
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { NotificationService } from '../services/notification.service';
import { getHttpErrorInfo, HttpErrorType } from '../utils/error-handler.utils';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const notificationService = inject(NotificationService);

  // Adiciona token apenas para requisições à API
  const token = authService.getToken();
  if (token && req.url.includes('/api/')) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      const errorInfo = getHttpErrorInfo(error);

      // Tratamento específico para erro 401 (não autorizado)
      if (error.status === 401) {
        authService.logout();
        notificationService.showError(
          'Sessão expirada. Faça login novamente.',
          'Sessão Expirada'
        );
        router.navigate(['/login']);
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

