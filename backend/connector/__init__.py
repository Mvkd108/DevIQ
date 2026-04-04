"""
Connector module for DevHouse26.

Provides provider-agnostic connector infrastructure for ingesting
data from GitHub, GitLab, Bitbucket, and other Git providers.
"""
from .providers.github import GitHubConnector

__all__ = ['GitHubConnector']
