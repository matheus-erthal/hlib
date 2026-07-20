"""Interfaces para o módulo de recuperação de dados."""

from .adapter import DataAdapter
from .portal import Portal

__all__ = [
    'DataAdapter',
    'Portal'
]