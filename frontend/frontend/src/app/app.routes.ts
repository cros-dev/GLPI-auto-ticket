import { Routes } from '@angular/router';
import { PasswordResetComponent } from './components/password-reset/password-reset';
import { SuccessComponent } from './components/success/success';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/password-reset',
    pathMatch: 'full'
  },
  {
    path: 'password-reset',
    component: PasswordResetComponent
  },
  {
    path: 'success',
    component: SuccessComponent
  },
  {
    path: '**',
    redirectTo: '/password-reset'
  }
];

