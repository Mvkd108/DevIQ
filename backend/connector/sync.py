"""
Sync orchestration for connector data ingestion.

Manages incremental and full sync operations with checkpointing
and error recovery.
"""

import logging
import time
from enum import Enum
from typing import Optional, Iterator, List, Callable
from datetime import datetime, timedelta

from .cursor import Cursor, CursorStore

logger = logging.getLogger(__name__)


class SyncMode(Enum):
    """Sync operation modes."""
    BACKFILL = "backfill"      # Historical sync from start date
    INCREMENTAL = "incremental"  # Changes since last sync
    FORCE_FULL = "force_full"    # Ignore cursor, full re-sync


class SyncOrchestrator:
    """
    Orchestrates sync operations between connectors and storage.
    
    Manages pagination, checkpointing, retries, and error recovery
    for efficient data ingestion.
    """
    
    def __init__(self, cursor_store: CursorStore, batch_size: int = 100):
        """
        Initialize sync orchestrator.
        
        Args:
            cursor_store: Store for persisting sync cursors
            batch_size: Number of records to process per batch
        """
        self.cursor_store = cursor_store
        self.batch_size = batch_size
        self._stop_requested = False
    
    def sync_repository(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str,
        fetcher: Callable[..., Iterator[dict]],
        mode: SyncMode = SyncMode.INCREMENTAL,
        start_date: Optional[datetime] = None
    ) -> dict:
        """
        Sync a repository's entities.
        
        Args:
            provider: Provider name (github, gitlab, etc.)
            repo_owner: Repository owner
            repo_name: Repository name
            entity_type: Type of entity (prs, ci_runs, deployments)
            fetcher: Generator function that yields entities from connector
            mode: Sync mode (backfill, incremental, force_full)
            start_date: For backfill mode, how far back to go
        
        Returns:
            Sync statistics dict
        """
        stats = {
            'entity_type': entity_type,
            'records_synced': 0,
            'batches': 0,
            'errors': 0,
            'started_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'status': 'running'
        }
        
        try:
            # Get or create cursor
            cursor = self._get_or_create_cursor(
                provider, repo_owner, repo_name, entity_type, mode, start_date
            )
            
            logger.info(
                f"Starting {mode.value} sync for {provider}:{repo_owner}/{repo_name} "
                f"({entity_type}) from page {cursor.page}"
            )
            
            # Process batches
            batch: List[dict] = []
            
            for entity in fetcher(page=cursor.page, since=cursor.last_synced_at):
                if self._stop_requested:
                    logger.info("Sync stopped by request")
                    stats['status'] = 'stopped'
                    break
                
                batch.append(entity)
                
                if len(batch) >= self.batch_size:
                    self._process_batch(batch, stats)
                    cursor.page += 1
                    cursor.has_more = True
                    self._save_checkpoint(provider, repo_owner, repo_name, cursor)
                    batch = []
            
            # Process remaining batch
            if batch:
                self._process_batch(batch, stats)
            
            # Mark sync complete
            cursor.has_more = False
            cursor.last_synced_at = datetime.utcnow()
            self._save_checkpoint(provider, repo_owner, repo_name, cursor)
            
            stats['status'] = 'completed'
            stats['completed_at'] = datetime.utcnow().isoformat()
            
            logger.info(
                f"Sync completed for {entity_type}: {stats['records_synced']} records "
                f"in {stats['batches']} batches"
            )
            
        except Exception as e:
            logger.error(f"Sync failed for {entity_type}: {e}")
            stats['status'] = 'failed'
            stats['errors'] += 1
            stats['error_message'] = str(e)
            raise
        
        return stats
    
    def _get_or_create_cursor(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str,
        mode: SyncMode,
        start_date: Optional[datetime]
    ) -> Cursor:
        """Get existing cursor or create new one based on mode."""
        if mode == SyncMode.FORCE_FULL:
            # Reset cursor for full re-sync
            self.cursor_store.reset_cursor(provider, repo_owner, repo_name, entity_type)
            return Cursor(
                entity_type=entity_type,
                last_synced_at=start_date,
                last_id=None,
                page=1,
                has_more=True
            )
        
        # Try to load existing cursor
        cursor = self.cursor_store.get_cursor(
            provider, repo_owner, repo_name, entity_type
        )
        
        if cursor and mode == SyncMode.INCREMENTAL:
            # Resume from last position
            cursor.has_more = True
            return cursor
        
        # Create new cursor for backfill
        effective_start = start_date or (datetime.utcnow() - timedelta(days=90))
        return Cursor(
            entity_type=entity_type,
            last_synced_at=effective_start,
            last_id=None,
            page=1,
            has_more=True
        )
    
    def _process_batch(self, batch: List[dict], stats: dict) -> None:
        """Process a batch of entities."""
        try:
            # This would persist to connector_* tables
            # Implementation depends on storage backend
            logger.debug(f"Processing batch of {len(batch)} records")
            stats['records_synced'] += len(batch)
            stats['batches'] += 1
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            stats['errors'] += 1
            raise
    
    def _save_checkpoint(
        self,
        provider: str,
        repo_owner: str,
        repo_name: str,
        cursor: Cursor
    ) -> None:
        """Save sync checkpoint."""
        try:
            self.cursor_store.save_cursor(provider, repo_owner, repo_name, cursor)
            logger.debug(f"Checkpoint saved for page {cursor.page}")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
    
    def stop(self) -> None:
        """Request sync to stop gracefully."""
        self._stop_requested = True
        logger.info("Sync stop requested")
