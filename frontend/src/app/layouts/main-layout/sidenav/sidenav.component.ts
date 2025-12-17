import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, PLATFORM_ID, Inject } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { RouterModule } from '@angular/router';
import { DrawerModule } from 'primeng/drawer';
import { PanelMenuModule } from 'primeng/panelmenu';
import { MenuItem } from 'primeng/api';
import { fromEvent, Subject } from 'rxjs';
import { takeUntil, debounceTime } from 'rxjs/operators';

/**
 * Componente de navegação lateral (sidenav).
 * 
 * Renderiza um menu de navegação que se adapta ao tamanho da tela:
 * - Desktop: Menu fixo no layout que empurra o conteúdo
 * - Mobile: Drawer overlay com backdrop modal
 * 
 * Utiliza detecção responsiva para alternar automaticamente entre os modos.
 */
@Component({
  selector: 'app-sidenav',
  standalone: true,
  imports: [CommonModule, RouterModule, DrawerModule, PanelMenuModule],
  templateUrl: './sidenav.component.html',
  styleUrl: './sidenav.component.css'
})
export class SidenavComponent implements OnInit, OnDestroy {
  /** Controla a visibilidade do sidenav. */
  @Input() visible = false;
  
  /** Emitido quando a visibilidade do sidenav muda. */
  @Output() visibleChange = new EventEmitter<boolean>();

  /** Indica se a aplicação está sendo executada em dispositivo mobile (largura < 768px). */
  isMobile = false;
  
  /** Subject para gerenciar unsubscribe de observables. */
  private destroy$ = new Subject<void>();

  /** Itens de menu exibidos no sidenav. */
  menuItems: MenuItem[] = [];

  constructor(@Inject(PLATFORM_ID) private platformId: Object) {
    this.initializeMenuItems();
  }

  /**
   * Inicializa os itens do menu.
   * 
   * @private
   */
  private initializeMenuItems(): void {
    this.menuItems = [
    {
      label: 'Início',
      icon: 'pi pi-home',
      routerLink: '/'
    },
    {
      label: 'Sugestões de Categorias',
      icon: 'pi pi-tags',
        routerLink: ['/category-suggestions'],
      items: [
          {
            label: 'Dashboard',
            icon: 'pi pi-chart-bar',
            routerLink: ['/category-suggestions']
          },
        {
          label: 'Pendentes',
          icon: 'pi pi-clock',
            routerLink: ['/category-suggestions'],
            queryParams: { status: 'pending' }
          },
          {
            label: 'Aprovadas',
            icon: 'pi pi-check-circle',
            routerLink: ['/category-suggestions'],
            queryParams: { status: 'approved' }
        }
      ]
    }
  ];
  }

  /**
   * Inicializa o componente configurando detecção de mobile e listener de resize.
   */
  ngOnInit(): void {
    if (isPlatformBrowser(this.platformId)) {
      this.checkMobile();
      fromEvent(window, 'resize')
        .pipe(
          debounceTime(100),
          takeUntil(this.destroy$)
        )
        .subscribe(() => this.checkMobile());
    }
  }

  /**
   * Limpa recursos ao destruir o componente.
   */
  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /**
   * Verifica se a largura da janela indica dispositivo mobile.
   * 
   * @private
   */
  private checkMobile(): void {
    this.isMobile = window.innerWidth < 768;
  }

  /**
   * Manipula o evento de fechamento do drawer (mobile).
   * 
   * Emite evento para atualizar o estado de visibilidade no componente pai.
   */
  onHide(): void {
    this.visibleChange.emit(false);
  }
}

