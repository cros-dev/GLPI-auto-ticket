import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { NotificationService } from '../../services/notification.service';

@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  username = '';
  password = '';
  loading = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private notificationService: NotificationService
  ) {
    // Se já estiver autenticado, redireciona
    if (this.authService.isAuthenticated()) {
      this.router.navigate(['/']);
    }
  }

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
        // Login bem-sucedido, redireciona para home
        setTimeout(() => {
          this.router.navigate(['/']);
        }, 500);
      },
      error: (err) => {
        this.loading = false;
        
        // Erro de conexão ou servidor indisponível
        if (!err.status || err.status === 0) {
          this.notificationService.showError(
            'Não foi possível conectar ao servidor. Verifique se o backend está rodando.',
            'Erro de Conexão'
          );
        } else if (err.status === 400 || err.status === 401) {
          this.notificationService.showError('Usuário ou senha inválidos', 'Erro de Autenticação');
        } else {
          this.notificationService.showError(
            'Erro ao fazer login. Tente novamente.',
            'Erro'
          );
        }
        console.error('Erro no login:', err);
      }
    });
  }
}
