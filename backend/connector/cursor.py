"""
Cursor management for incremental sync.

Tracks pagination and sync state to enable efficient
incremental updates without full rescans.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class Cursor:
    """
    Pagination and sync state cursor.
    
    Tracks where we left off in a sync operation to enable
    efficient incremental updates.
    """
    entity_type: str  # 'prs', 'ci_runs', 'deployments'
    last_synced_at: Optional[datetime]
    last_id: Optional[str]  # For offset pagination
    page: int  # Current page number
    has_more: bool  # Whether there are more pages
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cursor to dictionary for JSON serialization."""
        return {
            'entity_type': self.entity_type,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'last_id': self.last_id,
            'page': self.page,
            'has_more': self.has_more
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Cursor':
        """Create cursor from dictionary."""
        last_synced_at = None
        if data.get('last_synced_at'):
            try:
                last_synced_at = datetime.fromisoformat(data['last_synced_at'])
            except (ValueError, TypeError):
                pass
        
        return cls(
            entity_type=data.get('entity_type', ''),
            last_synced_at=last_synced_at,
            last_id=data.get('last_id'),
            page=data.get('page', 1),
            has_more=data.get('has_more', False)
        )


class CursorStore:
    """
    Store and retrieve sync cursors.
    
    Persists cursor state to enable resumable sync operations.
    """
    
    def __init__(self, storage_client=None):
        """
        Initialize cursor store.
        
        Args:
            storage_client: Client for persistent storage (e.g., Supabase)
        """
        self.storage = storage_client
        self._memory_cache: Dict[str, Cursor] = {}
    
    def _make_key(self, provider: str, repo_owner: str, repo_name: str, entity_type: str) -> str:
        """Create unique key for cursor."""
        return f"{provider}:{repo_owner}/{repo_name}:{entity_type}"
    
    def save_cursor(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        cursor: Cursor
    ) -> None:
        """
        Save cursor to persistent storage.
        
        Args:
            provider: Provider name (github, gitlab, etc.)
            repo_owner: Repository owner
            repo_name: Repository name
            cursor: Cursor to save
        """
        key = self._make_key(provider, repo_owner, repo_name, cursor.entity_type)
        
        # Always cache in memory
        self._memory_cache[key] = cursor
        
        # Persist to storage if available
        if self.storage:
            try:
                # This would use the actual storage client
                # Example: self.storage.table('connector_sync_state').upsert(...)
                logger.debug(f"Persisting cursor for {key}")
                # Implementation depends on storage backend
                self._persist_to_storage(provider, repo_owner, repo_name, cursor)
            except Exception as e:
                logger.warning(f"Failed to persist cursor {key}: {e}")
    
    def _persist_to_storage(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        cursor: Cursor
    ) -> None:
        """
        Persist cursor to storage backend.
        
        To be implemented with actual storage client.
        """
        # Placeholder for actual implementation
        # Would use Supabase/Postgres to store in connector_sync_state table
        raise NotImplementedError("Storage persistence not yet implemented")
    
    def get_cursor(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str
    ) -> Optional[Cursor]:
        """
        Retrieve cursor from storage.
        
        Args:
            provider: Provider name
            repo_owner: Repository owner
            repo_name: Repository name
            entity_type: Type of entity (prs, ci_runs, deployments)
        
        Returns:
            Cursor if found, None otherwise
        """
        key = self._make_key(provider, repo_owner, repo_name, entity_type)
        
        # Check memory cache first
        if key in self._memory_cache:
            return self._memory_cache[key]
        
        # Try to load from persistent storage
        if self.storage:
            try:
                cursor = self._load_from_storage(provider, repo_owner, repo_name, entity_type)
                if cursor:
                    self._memory_cache[key] = cursor
                return cursor
            except Exception as e:
                logger.warning(f"Failed to load cursor {key}: {e}")
        
        return None
    
    def _load_from_storage(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str
    ) -> Optional[Cursor]:
        """
        Load cursor from storage backend.
        
        To be implemented with actual storage client.
        """
        # Placeholder for actual implementation
        raise NotImplementedError("Storage persistence not yet implemented")
    
    def reset_cursor(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str
    ) -> None:
        """
        Reset cursor for entity type (force full re-sync).
        
        Args:
            provider: Provider name
            repo_owner: Repository owner
            repo_name: Repository name
            entity_type: Type of entity to reset
        """
        key = self._make_key(provider, repo_owner, repo_name, entity_type)
        
        # Remove from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        # Reset in persistent storage
        if self.storage:
            try:
                self._reset_in_storage(provider, repo_owner, repo_name, entity_type)
            except Exception as e:
                logger.warning(f"Failed to reset cursor {key}: {e}")
    
    def _reset_in_storage(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str
    ) -> None:
        """Reset cursor in storage backend."""
        # Placeholder for actual implementation
        raise NotImplementedError("Storage persistence not yet implemented")
