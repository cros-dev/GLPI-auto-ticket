import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

/**
 * Credenciais de login do usuário.
 */
export interface LoginCredentials {
  /** Nome de usuário. */
  username: string;
  /** Senha do usuário. */
  password: string;
}

/**
 * Resposta do endpoint de autenticação JWT.
 */
export interface LoginResponse {
  /** Access token JWT para autenticação. */
  access: string;
  /** Refresh token JWT para renovar o access token. */
  refresh: string;
}

/**
 * Resposta do endpoint de refresh token JWT.
 */
export interface RefreshTokenResponse {
  /** Novo access token JWT. */
  access: string;
}

/**
 * Serviço de autenticação.
 * 
 * Gerencia autenticação de usuários, armazenamento de token e estado
 * de autenticação da aplicação. Utiliza localStorage para persistência
 * do token e BehaviorSubject para reatividade.
 */
@Injectable({
  providedIn: 'root'
})
export class AuthService {
  /** URL base da API obtida do ambiente. */
  private apiUrl = environment.apiUrl;
  
  /** Chave utilizada para armazenar o access token no localStorage. */
  private accessTokenKey = 'access_token';
  
  /** Chave utilizada para armazenar o refresh token no localStorage. */
  private refreshTokenKey = 'refresh_token';
  
  /** Subject reativo para notificar mudanças no token. */
  private tokenSubject = new BehaviorSubject<string | null>(this.getStoredAccessToken());

  constructor(private http: HttpClient) {}

  /**
   * Realiza login no sistema e armazena os tokens JWT retornados.
   * 
   * @param credentials - Credenciais de login (username e password)
   * @returns Observable com a resposta contendo access e refresh tokens
   * 
   * @example
   * ```typescript
   * this.authService.login({ username: 'user', password: 'pass' })
   *   .subscribe(response => console.log('Access:', response.access));
   * ```
   */
  login(credentials: LoginCredentials): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(
      `${this.apiUrl}/token/`,
      {
        username: credentials.username,
        password: credentials.password
      }
    ).pipe(
      tap(response => {
        this.setTokens(response.access, response.refresh);
      })
    );
  }

  /**
   * Define e persiste os tokens JWT de autenticação.
   * 
   * @param accessToken - Access token JWT a ser armazenado
   * @param refreshToken - Refresh token JWT a ser armazenado
   */
  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(this.accessTokenKey, accessToken);
    localStorage.setItem(this.refreshTokenKey, refreshToken);
    this.tokenSubject.next(accessToken);
  }

  /**
   * Retorna o access token de autenticação atual.
   * 
   * @returns Access token atual ou null se não houver token armazenado
   */
  getToken(): string | null {
    return this.tokenSubject.value;
  }

  /**
   * Retorna o refresh token armazenado.
   * 
   * @returns Refresh token ou null se não existir
   */
  getRefreshToken(): string | null {
    return localStorage.getItem(this.refreshTokenKey);
  }

  /**
   * Recupera o access token armazenado no localStorage.
   * 
   * @returns Access token armazenado ou null se não existir
   */
  private getStoredAccessToken(): string | null {
    return localStorage.getItem(this.accessTokenKey);
  }

  /**
   * Verifica se o usuário está autenticado.
   * 
   * @returns true se há um token válido, false caso contrário
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Realiza logout removendo os tokens e limpando o estado de autenticação.
   */
  logout(): void {
    localStorage.removeItem(this.accessTokenKey);
    localStorage.removeItem(this.refreshTokenKey);
    this.tokenSubject.next(null);
  }

  /**
   * Renova o access token usando o refresh token.
   * 
   * @returns Observable com a nova resposta contendo o novo access token
   */
  refreshAccessToken(): Observable<RefreshTokenResponse> {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      return new Observable(observer => {
        observer.error(new Error('Refresh token não encontrado'));
      });
    }

    return this.http.post<RefreshTokenResponse>(
      `${this.apiUrl}/token/refresh/`,
      {
        refresh: refreshToken
      }
    ).pipe(
      tap(response => {
        // Mantém o refresh token existente, apenas atualiza o access token
        const currentRefreshToken = this.getRefreshToken() || '';
        this.setTokens(response.access, currentRefreshToken);
      })
    );
  }

  /**
   * Retorna um Observable para observar mudanças no token de autenticação.
   * 
   * Útil para componentes que precisam reagir a mudanças no estado de autenticação.
   * 
   * @returns Observable que emite o token atual ou null
   * 
   * @example
   * ```typescript
   * this.authService.getTokenObservable().subscribe(token => {
   *   if (token) {
   *     console.log('Usuário autenticado');
   *   }
   * });
   * ```
   */
  getTokenObservable(): Observable<string | null> {
    return this.tokenSubject.asObservable();
  }
}

