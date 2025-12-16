import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { NotificationService } from '../../services/notification.service';
import { CategorySuggestion } from '../../models/category-suggestion.interface';

@Component({
  selector: 'app-category-suggestions',
  imports: [CommonModule],
  templateUrl: './category-suggestions.html',
  styleUrl: './category-suggestions.css',
})
export class CategorySuggestions implements OnInit {
  suggestions: CategorySuggestion[] = [];
  loading = false;
  error: string | null = null;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router,
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    this.loadSuggestions();
  }

  loadSuggestions(): void {
    this.loading = true;
    this.error = null;

    this.apiService.getCategorySuggestions('pending').subscribe({
      next: (data) => {
        this.suggestions = data;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        if (!err.status || err.status === 0) {
          this.error = 'Não foi possível conectar ao servidor. Verifique se o backend está rodando.';
          this.notificationService.showError(
            'Não foi possível conectar ao servidor. Verifique se o backend está rodando.',
            'Erro de Conexão'
          );
        } else {
          this.error = 'Erro ao carregar sugestões.';
          this.notificationService.showError('Erro ao carregar sugestões.', 'Erro');
        }
        console.error('Erro ao carregar sugestões:', err);
      }
    });
  }

  approveSuggestion(id: number): void {
    this.apiService.approveCategorySuggestion(id).subscribe({
      next: () => {
        // Remove a sugestão da lista após aprovar
        this.suggestions = this.suggestions.filter(s => s.id !== id);
        this.notificationService.showSuccess('Sugestão aprovada com sucesso!');
      },
      error: (err) => {
        this.notificationService.showError('Erro ao aprovar sugestão. Tente novamente.', 'Erro');
        console.error('Erro ao aprovar:', err);
      }
    });
  }

  rejectSuggestion(id: number): void {
    // Usar confirm nativo por enquanto, pode ser substituído por Dialog do PrimeNG depois
    if (!confirm('Tem certeza que deseja rejeitar esta sugestão?')) {
      return;
    }

    this.apiService.rejectCategorySuggestion(id).subscribe({
      next: () => {
        // Remove a sugestão da lista após rejeitar
        this.suggestions = this.suggestions.filter(s => s.id !== id);
        this.notificationService.showSuccess('Sugestão rejeitada com sucesso!');
      },
      error: (err) => {
        this.notificationService.showError('Erro ao rejeitar sugestão. Tente novamente.', 'Erro');
        console.error('Erro ao rejeitar:', err);
      }
    });
  }

  formatDate(dateString: string | null): string {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString('pt-BR');
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
