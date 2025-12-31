import { Routes } from '@angular/router';
import { CategorySuggestions } from './components/category-suggestions/category-suggestions';
import { CategoryPreviewComponent } from './components/category-preview/category-preview';
import { GlpiSyncComponent } from './components/glpi-sync/glpi-sync';
import { KnowledgeBaseComponent } from './components/knowledge-base/knowledge-base';
import { Login } from './components/login/login';
import { PasswordResetComponent } from './components/password-reset/password-reset';
import { MainLayoutComponent } from './layouts/main-layout/main-layout.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    component: Login
  },
  {
    path: 'password-reset',
    component: PasswordResetComponent
  },
  {
    path: '',
    component: MainLayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        redirectTo: '/category-suggestions',
        pathMatch: 'full'
      },
      {
        path: 'category-suggestions',
        component: CategorySuggestions
      },
      {
        path: 'category-preview',
        component: CategoryPreviewComponent
      },
      {
        path: 'sync',
        component: GlpiSyncComponent
      },
      {
        path: 'knowledge-base',
        component: KnowledgeBaseComponent
      }
    ]
  }
];
