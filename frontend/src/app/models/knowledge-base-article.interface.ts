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
 * Interface para resposta de geração de artigo de Base de Conhecimento.
 */
export interface KnowledgeBaseArticleResponse {
  /** Texto completo do artigo gerado */
  article: string;
  
  /** Tipo do artigo gerado */
  article_type: string;
  
  /** Categoria informada */
  category: string;
}

