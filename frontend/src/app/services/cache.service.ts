import { Injectable } from '@angular/core';
import { Observable, of, BehaviorSubject } from 'rxjs';
import { tap, shareReplay } from 'rxjs/operators';

/**
 * Configuração de cache para uma chave específica.
 */
export interface CacheConfig {
  /** Tempo de expiração em milissegundos. Se não fornecido, o cache nunca expira. */
  ttl?: number;
}

/**
 * Item armazenado no cache com metadados.
 */
interface CacheItem<T> {
  data: T;
  timestamp: number;
  config?: CacheConfig;
}

/**
 * Serviço de cache reutilizável para armazenar resultados de requisições HTTP.
 * 
 * Permite cachear dados por chave, com suporte a TTL (Time To Live) opcional.
 * Útil para evitar requisições desnecessárias ao backend, melhorando performance
 * e experiência do usuário.
 * 
 * @example
 * ```typescript
 * // No componente ou service
 * constructor(private cacheService: CacheService) {}
 * 
 * getData(): Observable<Data[]> {
 *   const cacheKey = 'my-data';
 *   
 *   // Tenta buscar do cache
 *   const cached = this.cacheService.get<Data[]>(cacheKey);
 *   if (cached) {
 *     return of(cached);
 *   }
 *   
 *   // Se não tiver no cache, faz a requisição e cacheia
 *   return this.http.get<Data[]>('/api/data').pipe(
 *     tap(data => this.cacheService.set(cacheKey, data, { ttl: 60000 })) // 1 minuto
 *   );
 * }
 * ```
 */
@Injectable({
  providedIn: 'root'
})
export class CacheService {
  /** Armazenamento interno do cache. */
  private cache = new Map<string, CacheItem<any>>();

  /**
   * Obtém um valor do cache.
   * 
   * @param key - Chave do cache
   * @returns Valor cacheado ou null se não existir ou expirado
   */
  get<T>(key: string): T | null {
    const item = this.cache.get(key);
    
    if (!item) {
      return null;
    }

    // Verifica se expirou
    if (item.config?.ttl) {
      const age = Date.now() - item.timestamp;
      if (age > item.config.ttl) {
        this.cache.delete(key);
        return null;
      }
    }

    return item.data as T;
  }

  /**
   * Armazena um valor no cache.
   * 
   * @param key - Chave do cache
   * @param value - Valor a ser cacheado
   * @param config - Configuração opcional do cache (TTL, etc)
   */
  set<T>(key: string, value: T, config?: CacheConfig): void {
    this.cache.set(key, {
      data: value,
      timestamp: Date.now(),
      config
    });
  }

  /**
   * Remove um valor específico do cache.
   * 
   * @param key - Chave do cache a ser removida
   */
  delete(key: string): void {
    this.cache.delete(key);
  }

  /**
   * Remove todas as entradas do cache que começam com o prefixo fornecido.
   * Útil para limpar caches relacionados quando um item específico é atualizado.
   * 
   * @param prefix - Prefixo das chaves a serem removidas
   * 
   * @example
   * ```typescript
   * // Limpa todos os caches de 'category-suggestions'
   * cacheService.deleteByPrefix('category-suggestions');
   * ```
   */
  deleteByPrefix(prefix: string): void {
    const keysToDelete: string[] = [];
    this.cache.forEach((_, key) => {
      if (key.startsWith(prefix)) {
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach(key => this.cache.delete(key));
  }

  /**
   * Limpa todo o cache.
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Verifica se uma chave existe no cache e não está expirada.
   * 
   * @param key - Chave a ser verificada
   * @returns true se existe e não expirou, false caso contrário
   */
  has(key: string): boolean {
    const item = this.cache.get(key);
    
    if (!item) {
      return false;
    }

    // Verifica se expirou
    if (item.config?.ttl) {
      const age = Date.now() - item.timestamp;
      if (age > item.config.ttl) {
        this.cache.delete(key);
        return false;
      }
    }

    return true;
  }
}

