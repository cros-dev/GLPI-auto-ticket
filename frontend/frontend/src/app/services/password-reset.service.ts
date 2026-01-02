import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  PasswordResetRequest,
  PasswordResetRequestResponse,
  OtpValidationRequest,
  OtpValidationResponse,
  PasswordResetConfirmRequest,
  PasswordResetConfirmResponse
} from '../models/password-reset.interface';

/**
 * Serviço para reset de senha (SSPR - Self-Service Password Reset).
 * 
 * Fornece métodos para interagir com os endpoints de reset de senha:
 * - Solicitação de reset e envio de OTP via SMS
 * - Validação de código OTP
 * - Confirmação e execução do reset de senha
 */
@Injectable({
  providedIn: 'root'
})
export class PasswordResetService {
  /** URL base da API obtida do ambiente. */
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Solicita reset de senha e envia código OTP via SMS.
   * 
   * @param data - Dados da solicitação (email e sistema)
   * @returns Observable com a resposta contendo o token da solicitação
   * 
   * @example
   * ```typescript
   * this.passwordResetService.requestPasswordReset({
   *   identifier: 'usuario@exemplo.com',
   *   system: 'zoho'
   * }).subscribe(response => {
   *   console.log('Token:', response.data.token);
   * });
   * ```
   */
  requestPasswordReset(data: PasswordResetRequest): Observable<PasswordResetRequestResponse> {
    return this.http.post<PasswordResetRequestResponse>(
      `${this.apiUrl}/accounts/password-reset/request/`,
      data
    );
  }

  /**
   * Valida código OTP recebido via SMS.
   * 
   * @param data - Dados da validação (token e código OTP)
   * @returns Observable com a resposta da validação
   * 
   * @example
   * ```typescript
   * this.passwordResetService.validateOtp({
   *   token: 'token_da_solicitacao',
   *   otp_code: '123456'
   * }).subscribe(response => {
   *   if (response.valid) {
   *     console.log('OTP válido!');
   *   }
   * });
   * ```
   */
  validateOtp(data: OtpValidationRequest): Observable<OtpValidationResponse> {
    return this.http.post<OtpValidationResponse>(
      `${this.apiUrl}/accounts/password-reset/validate-otp/`,
      data
    );
  }

  /**
   * Confirma e executa o reset de senha.
   * 
   * @param data - Dados da confirmação (token e nova senha)
   * @returns Observable com a resposta da confirmação
   * 
   * @example
   * ```typescript
   * this.passwordResetService.confirmPasswordReset({
   *   token: 'token_da_solicitacao',
   *   new_password: 'NovaSenh@123'
   * }).subscribe(response => {
   *   if (response.success) {
   *     console.log('Senha resetada com sucesso!');
   *   }
   * });
   * ```
   */
  confirmPasswordReset(data: PasswordResetConfirmRequest): Observable<PasswordResetConfirmResponse> {
    return this.http.post<PasswordResetConfirmResponse>(
      `${this.apiUrl}/accounts/password-reset/confirm/`,
      data
    );
  }
}

