/**
 * Interfaces para reset de senha (SSPR).
 */

/**
 * Dados para solicitar reset de senha.
 */
export interface PasswordResetRequest {
  /** Email do usuário. */
  identifier: string;
  /** Sistema onde a senha será resetada. */
  system?: 'zoho' | 'ad' | 'both';
}

/**
 * Resposta da solicitação de reset de senha.
 */
export interface PasswordResetRequestResponse {
  /** Mensagem de resposta. */
  message: string;
  /** Dados da solicitação criada. */
  data: {
    /** Token da solicitação (usado para validar OTP e confirmar reset). */
    token: string;
    /** Email do usuário. */
    identifier: string;
    /** Sistema escolhido. */
    system: string;
    /** Status da solicitação. */
    status: string;
    /** Data de criação (formato ISO). */
    created_at: string;
    /** Data de expiração (formato ISO). */
    expires_at: string;
  };
}

/**
 * Dados para validar código OTP.
 */
export interface OtpValidationRequest {
  /** Token da solicitação de reset. */
  token: string;
  /** Código OTP de 6 dígitos. */
  otp_code: string;
}

/**
 * Resposta da validação de OTP.
 */
export interface OtpValidationResponse {
  /** Indica se o OTP é válido. */
  valid: boolean;
  /** Token da solicitação. */
  token: string;
  /** Mensagem sobre o status da validação. */
  message: string;
}

/**
 * Dados para confirmar reset de senha.
 */
export interface PasswordResetConfirmRequest {
  /** Token da solicitação de reset (após OTP validado). */
  token: string;
  /** Nova senha. */
  new_password: string;
}

/**
 * Resposta da confirmação de reset de senha.
 */
export interface PasswordResetConfirmResponse {
  /** Indica se o reset foi bem-sucedido. */
  success: boolean;
  /** Mensagem sobre o resultado. */
  message: string;
  /** Email do usuário que teve a senha resetada. */
  identifier: string;
}

