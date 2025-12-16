import { Routes } from '@angular/router';
import { CategorySuggestions } from './components/category-suggestions/category-suggestions';
import { Login } from './components/login/login';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    component: Login
  },
  {
    path: '',
    component: CategorySuggestions,
    canActivate: [authGuard]
  }
];
