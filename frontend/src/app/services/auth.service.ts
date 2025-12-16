import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private tokenKey = 'auth_token';
  private tokenSubject = new BehaviorSubject<string | null>(this.getStoredToken());

  constructor(private http: HttpClient) {}

  /**
   * Realiza login e armazena o token
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
   * Define o token e salva no localStorage
   */
  setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
    this.tokenSubject.next(token);
  }

  /**
   * Retorna o token atual
   */
  getToken(): string | null {
    return this.tokenSubject.value;
  }

  /**
   * Retorna o token salvo no localStorage
   */
  private getStoredToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  /**
   * Verifica se o usuário está autenticado
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Faz logout removendo o token
   */
  logout(): void {
    localStorage.removeItem(this.tokenKey);
    this.tokenSubject.next(null);
  }

  /**
   * Observable para observar mudanças no token
   */
  getTokenObservable(): Observable<string | null> {
    return this.tokenSubject.asObservable();
  }
}

