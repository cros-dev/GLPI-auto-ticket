import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';

/**
 * Componente de sucesso após reset de senha.
 */
@Component({
  selector: 'app-success',
  imports: [CommonModule, ButtonModule],
  templateUrl: './success.html',
  styleUrl: './success.css'
})
export class SuccessComponent {
  constructor(private router: Router) {}

  goToLogin(): void {
    // Redireciona para página de reset novamente (ou pode ser uma URL externa)
    this.router.navigate(['/password-reset']);
  }
}

