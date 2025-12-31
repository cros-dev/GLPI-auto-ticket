import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';
import { PasswordResetService } from '../../services/password-reset.service';
import { NotificationService } from '../../services/notification.service';
import { getHttpErrorInfo } from '../../utils/error-handler.utils';

/**
 * Componente de reset de senha (SSPR).
 * 
 * Permite que o usuário solicite reset de senha através de um fluxo em 3 etapas:
 * 1. Solicitação: Informa email e recebe OTP via SMS
 * 2. Validação: Informa código OTP recebido
 * 3. Confirmação: Define nova senha
 */
@Component({
  selector: 'app-password-reset',
  imports: [CommonModule, FormsModule, ButtonModule, InputTextModule, PasswordModule],
  templateUrl: './password-reset.html',
  styleUrl: './password-reset.css',
})
export class PasswordResetComponent {
  /** Email do usuário. */
  email = '';
  
  /** Código OTP recebido via SMS. */
  otpCode = '';
  
  /** Nova senha. */
  newPassword = '';
  
  /** Confirmação da nova senha. */
  confirmPassword = '';
  
  /** Token da solicitação de reset (retornado após solicitação). */
  token = '';
  
  /** Etapa atual do fluxo. */
  step: 'request' | 'validate' | 'confirm' = 'request';
  
  /** Indica se está processando uma requisição. */
  loading = false;

  constructor(
    private passwordResetService: PasswordResetService,
    private notificationService: NotificationService,
    public router: Router
  ) {}

  /**
   * Processa a solicitação de reset de senha.
   * 
   * Envia requisição para o backend que valida o usuário,
   * obtém telefone e envia OTP via SMS.
   */
  requestReset(): void {
    if (!this.email || !this.email.trim()) {
      this.notificationService.showWarning('Por favor, informe seu email');
      return;
    }

    // Validação básica de email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(this.email)) {
      this.notificationService.showWarning('Por favor, informe um email válido');
      return;
    }

    this.loading = true;

    this.passwordResetService.requestPasswordReset({
      identifier: this.email.trim().toLowerCase(),
      system: 'zoho'
    }).subscribe({
      next: (response) => {
        this.token = response.data.token;
        this.step = 'validate';
        this.loading = false;
        this.notificationService.showSuccess(
          response.message,
          'Código Enviado'
        );
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.notificationService.showError(
          errorInfo.message,
          'Erro ao Solicitar Reset'
        );
        console.error('Erro ao solicitar reset:', err);
      }
    });
  }

  /**
   * Valida o código OTP informado pelo usuário.
   * 
   * Verifica se o código OTP recebido via SMS está correto.
   */
  validateOtp(): void {
    if (!this.otpCode || !this.otpCode.trim()) {
      this.notificationService.showWarning('Por favor, informe o código OTP');
      return;
    }

    // Validação: código deve ter 6 dígitos
    const otpRegex = /^\d{6}$/;
    if (!otpRegex.test(this.otpCode.trim())) {
      this.notificationService.showWarning('O código OTP deve conter 6 dígitos');
      return;
    }

    if (!this.token) {
      this.notificationService.showError('Token não encontrado. Por favor, solicite um novo reset');
      this.resetForm();
      return;
    }

    this.loading = true;

    this.passwordResetService.validateOtp({
      token: this.token,
      otp_code: this.otpCode.trim()
    }).subscribe({
      next: (response) => {
        if (response.valid) {
          this.step = 'confirm';
          this.loading = false;
          this.notificationService.showSuccess(
            response.message,
            'OTP Validado'
          );
        } else {
          this.loading = false;
          this.notificationService.showError(
            'Código OTP inválido. Verifique o código e tente novamente.',
            'Código Inválido'
          );
        }
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.notificationService.showError(
          errorInfo.message,
          'Erro ao Validar OTP'
        );
        console.error('Erro ao validar OTP:', err);
      }
    });
  }

  /**
   * Confirma e executa o reset de senha.
   * 
   * Define a nova senha após validação do OTP.
   */
  confirmReset(): void {
    if (!this.newPassword || !this.confirmPassword) {
      this.notificationService.showWarning('Por favor, preencha os campos de senha');
      return;
    }

    // Validação: senhas devem ser iguais
    if (this.newPassword !== this.confirmPassword) {
      this.notificationService.showWarning('As senhas não coincidem');
      return;
    }

    // Validação: senha deve ter no mínimo 8 caracteres
    if (this.newPassword.length < 8) {
      this.notificationService.showWarning('A senha deve ter no mínimo 8 caracteres');
      return;
    }

    // Validação: senha deve conter pelo menos uma letra maiúscula, minúscula e número
    const hasUpper = /[A-Z]/.test(this.newPassword);
    const hasLower = /[a-z]/.test(this.newPassword);
    const hasDigit = /\d/.test(this.newPassword);

    if (!hasUpper || !hasLower || !hasDigit) {
      this.notificationService.showWarning(
        'A senha deve conter pelo menos uma letra maiúscula, uma minúscula e um número'
      );
      return;
    }

    if (!this.token) {
      this.notificationService.showError('Token não encontrado. Por favor, solicite um novo reset');
      this.resetForm();
      return;
    }

    this.loading = true;

    this.passwordResetService.confirmPasswordReset({
      token: this.token,
      new_password: this.newPassword
    }).subscribe({
      next: (response) => {
        this.loading = false;
        this.notificationService.showSuccess(
          response.message,
          'Senha Resetada'
        );
        // Redireciona para login após 2 segundos
        setTimeout(() => {
          this.router.navigate(['/login']);
        }, 2000);
      },
      error: (err) => {
        this.loading = false;
        const errorInfo = getHttpErrorInfo(err);
        this.notificationService.showError(
          errorInfo.message,
          'Erro ao Resetar Senha'
        );
        console.error('Erro ao confirmar reset:', err);
      }
    });
  }

  /**
   * Volta para a etapa anterior.
   */
  goBack(): void {
    if (this.step === 'validate') {
      this.step = 'request';
      this.otpCode = '';
    } else if (this.step === 'confirm') {
      this.step = 'validate';
      this.newPassword = '';
      this.confirmPassword = '';
    }
  }

  /**
   * Reseta o formulário e volta para a etapa inicial.
   */
  resetForm(): void {
    this.email = '';
    this.otpCode = '';
    this.newPassword = '';
    this.confirmPassword = '';
    this.token = '';
    this.step = 'request';
  }
}

