/**
 * Interface para requisição de geração de artigo de Base de Conhecimento.
 */
export interface KnowledgeBaseArticleRequest {
  /** Tipo do artigo: 'conceitual', 'operacional' ou 'troubleshooting' */
  article_type: 'conceitual' | 'operacional' | 'troubleshooting';
  
  /** Categoria da Base de Conhecimento (ex: 'RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher > Playout') */
  category: string;
  
  /** Contexto do ambiente, sistemas, servidores, softwares envolvidos */
  context: string;
}

/**
 * Interface para um artigo individual de Base de Conhecimento.
 */
export interface KnowledgeBaseArticleItem {
  /** Texto completo do artigo */
  content: string;
}

/**
 * Interface para resposta de geração de artigo de Base de Conhecimento.
 */
export interface KnowledgeBaseArticleResponse {
  /** Lista de artigos gerados (pode conter múltiplos artigos) */
  articles: KnowledgeBaseArticleItem[];
  
  /** Tipo do artigo gerado */
  article_type: string;
  
  /** Categoria informada */
  category: string;
}

