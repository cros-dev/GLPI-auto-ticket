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
   * Obtém detalhes de uma sugestão de categoria específica.
   * 
   * @param id - ID da sugestão
   * @returns Observable com detalhes da sugestão
   */
  getCategorySuggestion(id: number): Observable<CategorySuggestion> {
    const url = `${this.apiUrl}/category-suggestions/${id}/`;
    return this.http.get<CategorySuggestion>(url);
  }

  /**
   * Atualiza uma sugestão de categoria pendente.
   * 
   * @param id - ID da sugestão a ser atualizada
   * @param suggestedPath - Novo caminho da categoria sugerida
   * @param notes - Notas opcionais sobre a sugestão
   * @returns Observable com resposta da API
   */
  updateCategorySuggestion(
    id: number,
    suggestedPath: string,
    notes?: string
  ): Observable<any> {
    const url = `${this.apiUrl}/category-suggestions/${id}/`;
    const body: any = { suggested_path: suggestedPath };
    if (notes !== undefined) {
      body.notes = notes;
    }
    return this.http.patch(url, body);
  }

  /**
   * Gera uma prévia de sugestão de categoria sem salvar no banco.
   * 
   * Útil para testar e validar sugestões antes de criar tickets ou categorias.
   * Primeiro tenta encontrar uma categoria existente. Se não encontrar, gera uma nova sugestão.
   * 
   * @param title - Título do ticket
   * @param content - Conteúdo/descrição do ticket
   * @returns Observable com sugestão de categoria (categoria existente ou nova sugestão)
   * 
   * @example
   * ```typescript
   * this.apiService.previewCategorySuggestion('Título', 'Conteúdo').subscribe(result => {
   *   console.log('Categoria sugerida:', result.suggested_path);
   *   console.log('Método:', result.classification_method);
   * });
   * ```
   */
  previewCategorySuggestion(title: string, content: string): Observable<{
    suggested_path: string;
    suggested_category_id?: number;
    ticket_type?: number;
    ticket_type_label?: string;
    classification_method: 'existing_category' | 'new_suggestion';
    confidence?: string;
    note: string;
  }> {
    const url = `${this.apiUrl}/category-suggestions/preview/`;
    const body = { title, content };
    return this.http.post<{
      suggested_path: string;
      suggested_category_id?: number;
      ticket_type?: number;
      ticket_type_label?: string;
      classification_method: 'existing_category' | 'new_suggestion';
      confidence?: string;
      note: string;
    }>(url, body);
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

  /**
   * Sincroniza categorias do GLPI a partir da API (backend faz a integração).
   *
   * Endpoint: POST /api/glpi/categories/sync-from-api/
   *
   * @returns Observable com estatísticas da sincronização
   */
  syncGlpiCategoriesFromApi(): Observable<{
    created: number;
    updated: number;
    deleted: number;
    total: number;
  }> {
    const url = `${this.apiUrl}/glpi/categories/sync-from-api/`;
    return this.http.post<{
      created: number;
      updated: number;
      deleted: number;
      total: number;
    }>(url, {});
  }
}

