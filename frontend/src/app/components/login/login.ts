import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo, HttpErrorType } from '../../utils/error-handler.utils';

/**
 * Componente de login da aplicação.
 * 
 * Permite que o usuário faça autenticação no sistema utilizando
 * username e password. Após login bem-sucedido, redireciona para a página principal.
 */
@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  /** Username do usuário. */
  username = '';
  
  /** Senha do usuário. */
  password = '';
  
  /** Indica se está processando o login. */
  loading = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private notificationService: NotificationService
  ) {
    // Se já estiver autenticado, redireciona para home
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/']);
    }
  }

  /**
   * Processa o submit do formulário de login.
   * 
   * Valida os campos e realiza a autenticação via AuthService.
   * Em caso de sucesso, redireciona para a página principal após 500ms.
   */
  onSubmit(): void {
    if (!this.username || !this.password) {
      this.notificationService.showWarning('Por favor, preencha usuário e senha');
      return;
    }

    this.loading = true;

    this.authService.login({
      username: this.username,
      password: this.password
    }).subscribe({
      next: () => {
        this.loading = false;
        this.notificationService.showSuccess('Login realizado com sucesso!');
        // Redireciona após breve delay para melhor UX
        setTimeout(() => {
          this.router.navigate(['/']);
        }, 500);
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        
        // Mensagem específica para erro de autenticação
        const message = errorInfo.type === HttpErrorType.AUTHENTICATION || 
                       errorInfo.type === HttpErrorType.VALIDATION
          ? 'Usuário ou senha inválidos'
          : errorInfo.message;
        
        this.notificationService.showError(message, 'Erro de Autenticação');
        console.error('Erro no login:', err);
      }
    });
  }
}
