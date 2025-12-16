import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CategorySuggestion } from '../models/category-suggestion.interface';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  /**
   * Lista todas as sugestões de categorias pendentes
   */
  getCategorySuggestions(status?: 'pending' | 'approved' | 'rejected'): Observable<CategorySuggestion[]> {
    let url = `${this.apiUrl}/category-suggestions/`;
    if (status) {
      url += `?status=${status}`;
    }
    return this.http.get<CategorySuggestion[]>(url);
  }

  /**
   * Aprova uma sugestão de categoria
   */
  approveCategorySuggestion(id: number, notes?: string): Observable<any> {
    const url = `${this.apiUrl}/category-suggestions/${id}/approve/`;
    const body = notes ? { notes } : {};
    return this.http.post(url, body);
  }

  /**
   * Rejeita uma sugestão de categoria
   */
  rejectCategorySuggestion(id: number, notes?: string): Observable<any> {
    const url = `${this.apiUrl}/category-suggestions/${id}/reject/`;
    const body = notes ? { notes } : {};
    return this.http.post(url, body);
  }
}

