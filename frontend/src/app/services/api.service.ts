import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CategorySuggestion } from '../models/category-suggestion.interface';
import { CategorySuggestionStats } from '../models/category-suggestion-stats.interface';

/**
 * Serviço para comunicação com a API REST do backend.
 * 
 * Fornece métodos para interagir com os endpoints da API,
 * incluindo operações relacionadas a sugestões de categorias.
 */
@Injectable({
  providedIn: 'root'
})
export class ApiService {
  /** URL base da API obtida do ambiente. */
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Lista sugestões de categorias com filtro opcional por status.
   * 
   * @param status - Status para filtrar as sugestões (pending, approved, rejected). Se não informado, retorna todas.
   * @returns Observable com array de sugestões de categorias
   * 
   * @example
   * ```typescript
   * // Buscar apenas pendentes
   * this.apiService.getCategorySuggestions('pending').subscribe(...);
   * 
   * // Buscar todas
   * this.apiService.getCategorySuggestions().subscribe(...);
   * ```
   */
  getCategorySuggestions(status?: 'pending' | 'approved' | 'rejected'): Observable<CategorySuggestion[]> {
    let url = `${this.apiUrl}/category-suggestions/`;
    if (status) {
      url += `?status=${status}`;
    }
    return this.http.get<CategorySuggestion[]>(url);
  }

  /**
   * Aprova uma sugestão de categoria.
   * 
   * @param id - ID da sugestão a ser aprovada
   * @param notes - Notas opcionais sobre a aprovação
   * @returns Observable com resposta da API
   */
  approveCategorySuggestion(id: number, notes?: string): Observable<any> {
    const url = `${this.apiUrl}/category-suggestions/${id}/approve/`;
    const body = notes ? { notes } : {};
    return this.http.post(url, body);
  }

  /**
   * Rejeita uma sugestão de categoria.
   * 
   * @param id - ID da sugestão a ser rejeitada
   * @param notes - Notas opcionais sobre a rejeição
   * @returns Observable com resposta da API
   */
  rejectCategorySuggestion(id: number, notes?: string): Observable<any> {
    const url = `${this.apiUrl}/category-suggestions/${id}/reject/`;
    const body = notes ? { notes } : {};
    return this.http.post(url, body);
  }

  /**
   * Obtém estatísticas agregadas das sugestões de categorias.
   * 
   * @returns Observable com estatísticas (total, pending, approved, rejected)
   * 
   * @example
   * ```typescript
   * this.apiService.getCategorySuggestionStats().subscribe(stats => {
   *   console.log('Total:', stats.total);
   *   console.log('Pendentes:', stats.pending);
   * });
   * ```
   */
  getCategorySuggestionStats(): Observable<CategorySuggestionStats> {
    const url = `${this.apiUrl}/category-suggestions/stats/`;
    return this.http.get<CategorySuggestionStats>(url);
  }
}

