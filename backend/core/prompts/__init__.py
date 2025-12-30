"""
Módulo de prompts para classificação de tickets e geração de Base de Conhecimento.

Este pacote contém os templates de prompts organizados por funcionalidade:
- classification: Prompts para classificação e sugestão de categorias de tickets
- knowledge_base: Prompts para geração de artigos de Base de Conhecimento
"""

from .classification import get_classification_prompt, get_suggestion_prompt
from .knowledge_base import get_knowledge_base_prompt

__all__ = [
    'get_classification_prompt',
    'get_suggestion_prompt',
    'get_knowledge_base_prompt',
]

