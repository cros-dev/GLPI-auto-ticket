import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

/**
 * Item de breadcrumb.
 */
export interface BreadcrumbItem {
  /** Texto exibido no breadcrumb. */
  label: string;
  /** Rota para navegação (opcional). Se não fornecido, o item será exibido sem link. */
  route?: string | string[];
}

/**
 * Componente de breadcrumb reutilizável.
 * 
 * Exibe uma navegação hierárquica (breadcrumb) para indicar a localização
 * atual do usuário na aplicação. Os itens podem ter rotas opcionais para
 * navegação, ou ser apenas texto se for o item atual.
 * 
 * @example
 * ```typescript
 * // No componente
 * breadcrumbItems: BreadcrumbItem[] = [
 *   { label: 'Início', route: '/' },
 *   { label: 'Sugestões de Categorias', route: '/category-suggestions' },
 *   { label: 'Detalhes' } // sem route = item atual
 * ];
 * ```
 * 
 * ```html
 * <app-breadcrumb [items]="breadcrumbItems"></app-breadcrumb>
 * ```
 */
@Component({
  selector: 'app-breadcrumb',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './breadcrumb.html',
  styleUrl: './breadcrumb.css'
})
export class BreadcrumbComponent {
  /** Lista de itens do breadcrumb. */
  @Input() items: BreadcrumbItem[] = [];

  /**
   * Verifica se um item é o último da lista (item atual).
   * 
   * @param index - Índice do item
   * @returns true se for o último item
   */
  isLastItem(index: number): boolean {
    return index === this.items.length - 1;
  }
}

