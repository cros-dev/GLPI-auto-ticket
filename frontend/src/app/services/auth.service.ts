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
 * Resposta do endpoint de autenticação.
 */
export interface LoginResponse {
  /** Token de autenticação retornado pela API. */
  token: string;
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
  
  /** Chave utilizada para armazenar o token no localStorage. */
  private tokenKey = 'auth_token';
  
  /** Subject reativo para notificar mudanças no token. */
  private tokenSubject = new BehaviorSubject<string | null>(this.getStoredToken());

  constructor(private http: HttpClient) {}

  /**
   * Realiza login no sistema e armazena o token retornado.
   * 
   * @param credentials - Credenciais de login (username e password)
   * @returns Observable com a resposta contendo o token
   * 
   * @example
   * ```typescript
   * this.authService.login({ username: 'user', password: 'pass' })
   *   .subscribe(response => console.log('Token:', response.token));
   * ```
   */
  login(credentials: LoginCredentials): Observable<LoginResponse> {
    const body = `username=${encodeURIComponent(credentials.username)}&password=${encodeURIComponent(credentials.password)}`;

    return this.http.post<LoginResponse>(
      `${this.apiUrl}/accounts/token/`,
      body,
      {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      }
    ).pipe(
      tap(response => {
        this.setToken(response.token);
      })
    );
  }

  /**
   * Define e persiste o token de autenticação.
   * 
   * @param token - Token de autenticação a ser armazenado
   */
  setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
    this.tokenSubject.next(token);
  }

  /**
   * Retorna o token de autenticação atual.
   * 
   * @returns Token atual ou null se não houver token armazenado
   */
  getToken(): string | null {
    return this.tokenSubject.value;
  }

  /**
   * Recupera o token armazenado no localStorage.
   * 
   * @returns Token armazenado ou null se não existir
   */
  private getStoredToken(): string | null {
    return localStorage.getItem(this.tokenKey);
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
   * Realiza logout removendo o token e limpando o estado de autenticação.
   */
  logout(): void {
    localStorage.removeItem(this.tokenKey);
    this.tokenSubject.next(null);
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

