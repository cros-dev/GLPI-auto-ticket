import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProgressSpinnerModule } from 'primeng/progressspinner';

/**
 * Componente de loading reutilizável usando PrimeNG ProgressSpinner.
 * 
 * Exibe um spinner de carregamento com uma mensagem opcional.
 * 
 * @example
 * ```html
 * <app-loading [loading]="isLoading"></app-loading>
 * 
 * <!-- Com mensagem customizada -->
 * <app-loading [loading]="isLoading" message="Carregando dados..."></app-loading>
 * ```
 */
@Component({
  selector: 'app-loading',
  standalone: true,
  imports: [CommonModule, ProgressSpinnerModule],
  templateUrl: './loading.component.html',
  styleUrl: './loading.component.css'
})
export class LoadingComponent {
  /**
   * Controla se o loading deve ser exibido.
   * @default false
   */
  @Input() loading: boolean = false;

  /**
   * Mensagem a ser exibida junto com o spinner.
   * Se não fornecida, exibe a mensagem padrão.
   * @default 'Carregando...'
   */
  @Input() message: string = 'Carregando...';
}
