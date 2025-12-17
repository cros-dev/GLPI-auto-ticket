import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Guard de autenticação para proteger rotas.
 * 
 * Verifica se o usuário está autenticado antes de permitir acesso a uma rota.
 * Se não estiver autenticado, redireciona para a página de login.
 * 
 * @param route - Informações da rota ativada
 * @param state - Estado atual do router
 * @returns true se autenticado, false caso contrário (redireciona para login)
 * 
 * @example
 * ```typescript
 * // Em app.routes.ts
 * {
 *   path: 'dashboard',
 *   component: DashboardComponent,
 *   canActivate: [authGuard]
 * }
 * ```
 */
export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  // Redireciona para login se não estiver autenticado
  router.navigate(['/login']);
  return false;
};



