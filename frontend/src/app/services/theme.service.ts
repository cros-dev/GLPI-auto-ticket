import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type ThemeMode = 'light' | 'dark';
export type ThemePreference = ThemeMode | 'system';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly storageKey = 'theme.mode';
  private readonly darkClass = 'app-dark';
  private mediaQueryList: MediaQueryList | null = null;
  private mediaQueryListener: ((event: MediaQueryListEvent) => void) | null = null;

  constructor(@Inject(PLATFORM_ID) private platformId: Object) {}

  init(): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    const saved = this.getSavedPreference();
    // Requisito: alternar entre claro/escuro, com suporte a "system" (default)
    this.applyPreference(saved ?? 'system');
  }

  getMode(): ThemeMode {
    return this.isDarkApplied() ? 'dark' : 'light';
  }

  getPreference(): ThemePreference {
    return this.getSavedPreference() ?? 'system';
  }

  setPreference(pref: ThemePreference): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    localStorage.setItem(this.storageKey, pref);
    this.applyPreference(pref);
  }

  setMode(mode: ThemeMode): void {
    this.setPreference(mode);
  }

  toggle(): void {
    // Toggle simples: alterna entre light/dark (independente do system)
    this.setMode(this.getMode() === 'dark' ? 'light' : 'dark');
  }

  private applyPreference(pref: ThemePreference): void {
    this.detachSystemListener();
    if (pref === 'system') {
      this.attachSystemListener();
      this.applyMode(this.getSystemMode());
      return;
    }
    this.applyMode(pref);
  }

  private applyMode(mode: ThemeMode): void {
    const el = document.documentElement;
    el.classList.toggle(this.darkClass, mode === 'dark');
  }

  private isDarkApplied(): boolean {
    return document.documentElement.classList.contains(this.darkClass);
  }

  private getSavedPreference(): ThemePreference | null {
    const raw = localStorage.getItem(this.storageKey);
    if (raw === 'dark' || raw === 'light' || raw === 'system') {
      return raw as ThemePreference;
    }
    return null;
  }

  private getSystemMode(): ThemeMode {
    if (!this.mediaQueryList) {
      this.mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');
    }
    return this.mediaQueryList.matches ? 'dark' : 'light';
  }

  private attachSystemListener(): void {
    this.mediaQueryList = window.matchMedia('(prefers-color-scheme: dark)');
    this.mediaQueryListener = (event: MediaQueryListEvent) => {
      const saved = this.getSavedPreference();
      if (saved !== 'system') {
        return;
      }
      this.applyMode(event.matches ? 'dark' : 'light');
    };
    this.mediaQueryList.addEventListener('change', this.mediaQueryListener);
  }

  private detachSystemListener(): void {
    if (this.mediaQueryList && this.mediaQueryListener) {
      this.mediaQueryList.removeEventListener('change', this.mediaQueryListener);
    }
    this.mediaQueryList = null;
    this.mediaQueryListener = null;
  }
}


