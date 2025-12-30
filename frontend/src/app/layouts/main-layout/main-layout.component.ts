import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, RouterOutlet } from '@angular/router';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { TopbarComponent } from './topbar/topbar.component';
import { SidenavComponent } from './sidenav/sidenav.component';

/**
 * Componente de layout principal da aplicação.
 * 
 * Define a estrutura base do layout com topbar, sidenav e área de conteúdo.
 * Gerencia o estado de visibilidade do sidenav e coordena a comunicação
 * entre os componentes filhos (TopbarComponent e SidenavComponent).
 */
@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    RouterOutlet,
    ConfirmDialogModule,
    TopbarComponent,
    SidenavComponent
  ],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.css'
})
export class MainLayoutComponent {
  /** Controla se o sidenav está visível ou não. */
  sidenavVisible = false;

  /**
   * Alterna o estado de visibilidade do sidenav.
   * 
   * Chamado pelo TopbarComponent quando o usuário clica no botão de toggle.
   */
  onToggleSidenav(): void {
    this.sidenavVisible = !this.sidenavVisible;
  }
}

