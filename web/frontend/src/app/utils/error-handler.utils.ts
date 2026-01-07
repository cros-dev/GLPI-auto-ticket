/**
 * Utilitários para tratamento e análise de erros HTTP.
 */

/**
 * Tipos de erro HTTP identificados pela aplicação.
 */
export enum HttpErrorType {
  CONNECTION = 'CONNECTION',
  AUTHENTICATION = 'AUTHENTICATION',
  AUTHORIZATION = 'AUTHORIZATION',
  NOT_FOUND = 'NOT_FOUND',
  VALIDATION = 'VALIDATION',
  SERVER = 'SERVER',
  UNKNOWN = 'UNKNOWN'
}

/**
 * Informações sobre um erro HTTP.
 */
export interface HttpErrorInfo {
  type: HttpErrorType;
  message: string;
  statusCode?: number;
}

/**
 * Analisa um erro HTTP e retorna informações estruturadas.
 * 
 * @param error - Erro HTTP do Angular
 * @returns Informações estruturadas sobre o erro
 * 
 * @example
 * ```typescript
 * catchError((err: HttpErrorResponse) => {
 *   const errorInfo = getHttpErrorInfo(err);
 *   notificationService.showError(errorInfo.message);
 * })
 * ```
 */
export function getHttpErrorInfo(error: any): HttpErrorInfo {
  // Erro de conexão ou servidor indisponível
  if (!error.status || error.status === 0) {
    return {
      type: HttpErrorType.CONNECTION,
      message: 'Não foi possível conectar ao servidor. Verifique se o backend está rodando.'
    };
  }

  const status = error.status;

  // Erro de autenticação (401)
  if (status === 401) {
    return {
      type: HttpErrorType.AUTHENTICATION,
      message: 'Sessão expirada. Faça login novamente.',
      statusCode: status
    };
  }

  // Erro de autorização (403)
  if (status === 403) {
    return {
      type: HttpErrorType.AUTHORIZATION,
      message: 'Você não tem permissão para realizar esta ação.',
      statusCode: status
    };
  }

  // Não encontrado (404)
  if (status === 404) {
    return {
      type: HttpErrorType.NOT_FOUND,
      message: 'Recurso não encontrado.',
      statusCode: status
    };
  }

  // Erro de validação (400)
  if (status === 400) {
    const message = error.error?.detail || error.error?.message || 'Dados inválidos. Verifique os campos.';
    return {
      type: HttpErrorType.VALIDATION,
      message,
      statusCode: status
    };
  }

  // Erro do servidor (500+)
  if (status >= 500) {
    return {
      type: HttpErrorType.SERVER,
      message: 'Erro interno do servidor. Tente novamente mais tarde.',
      statusCode: status
    };
  }

  // Erro desconhecido
  return {
    type: HttpErrorType.UNKNOWN,
    message: error.error?.message || 'Ocorreu um erro inesperado. Tente novamente.',
    statusCode: status
  };
}

