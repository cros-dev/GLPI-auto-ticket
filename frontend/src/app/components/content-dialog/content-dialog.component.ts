import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DialogModule } from 'primeng/dialog';
import { ButtonModule } from 'primeng/button';

/**
 * Componente de dialog reutilizável para exibir conteúdo em modal.
 * 
 * Usa o Dialog do PrimeNG para exibir conteúdo longo, como textos de tickets,
 * com scroll automático quando o conteúdo excede a viewport.
 * 
 * @example
 * ```html
 * <app-content-dialog
 *   [visible]="showDialog"
 *   title="Conteúdo do Ticket"
 *   [content]="ticketContent"
 *   (visibleChange)="showDialog = $event">
 * </app-content-dialog>
 * ```
 */
@Component({
  selector: 'app-content-dialog',
  standalone: true,
  imports: [CommonModule, DialogModule, ButtonModule],
  templateUrl: './content-dialog.component.html',
  styleUrls: ['./content-dialog.component.css']
})
export class ContentDialogComponent {
  /**
   * Controla a visibilidade do dialog.
   * @default false
   */
  @Input() visible: boolean = false;

  /**
   * Título do dialog exibido no header.
   * @default 'Conteúdo'
   */
  @Input() title: string = 'Conteúdo';

  /**
   * Conteúdo a ser exibido no dialog.
   * Pode conter HTML ou texto simples.
   */
  @Input() content: string | null | undefined = '';

  /**
   * Evento emitido quando a visibilidade do dialog muda.
   * Permite two-way binding: [(visible)]="showDialog"
   */
  @Output() visibleChange = new EventEmitter<boolean>();

  /**
   * Estilo para o conteúdo do dialog com scroll automático.
   */
  contentStyle = {
    'max-height': '60vh',
    'overflow-y': 'auto'
  };

  /**
   * Fecha o dialog.
   */
  closeDialog(): void {
    this.visible = false;
    this.visibleChange.emit(false);
  }
}
