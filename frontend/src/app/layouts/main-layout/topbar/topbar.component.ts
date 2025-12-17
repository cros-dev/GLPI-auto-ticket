import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';
import { MenuModule } from 'primeng/menu';
import { MenuItem } from 'primeng/api';
import { AuthService } from '../../../services/auth.service';

/**
 * Componente da barra superior (topbar) do layout principal.
 * 
 * Exibe logo, título da aplicação, botão para toggle do sidenav
 * e menu do usuário com opções de perfil e logout.
 */
@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [CommonModule, RouterModule, ToolbarModule, ButtonModule, MenuModule],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.css'
})
export class TopbarComponent {
  /** Evento emitido quando o usuário clica no botão de toggle do sidenav. */
  @Output() toggleSidenav = new EventEmitter<void>();

  /** Itens do menu do usuário (perfil, logout, etc). */
  userMenuItems: MenuItem[] = [];

  constructor(
    private authService: AuthService,
    private router: Router
  ) {
    this.initializeUserMenu();
  }

  /**
   * Inicializa os itens do menu do usuário.
   * 
   * @private
   */
  private initializeUserMenu(): void {
    this.userMenuItems = [
      {
        label: 'Perfil',
        icon: 'pi pi-user',
        command: () => {
          // TODO: Implementar navegação para perfil quando necessário
        }
      },
      {
        separator: true
      },
      {
        label: 'Sair',
        icon: 'pi pi-sign-out',
        command: () => {
          this.logout();
        }
      }
    ];
  }

  /**
   * Emite evento para alternar a visibilidade do sidenav.
   * 
   * Chamado quando o usuário clica no botão de menu (hamburger).
   */
  onToggleSidenav(): void {
    this.toggleSidenav.emit();
  }

  /**
   * Realiza logout do usuário e redireciona para a página de login.
   */
  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}

