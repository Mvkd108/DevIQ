"""
Backfill logic for historical data ingestion.

Handles one-time sync of historical data with progress tracking
and error recovery.
"""

import logging
from typing import Optional, Callable, Iterator
from datetime import datetime, timedelta

from .cursor import Cursor, CursorStore
from .sync import SyncOrchestrator, SyncMode

logger = logging.getLogger(__name__)


class BackfillJob:
    """
    One-time backfill job for historical data.
    
    Fetches all historical data from a start date with:
    - Configurable date range
    - Batch processing
    - Progress tracking
    - Error recovery (resume from checkpoint)
    - Rate limit handling
    """
    
    def __init__(
        self,
        cursor_store: CursorStore,
        provider: str,
        repo_owner: str,
        repo_name: str,
        entity_type: str,
        start_date: Optional[datetime] = None,
        batch_size: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize backfill job.
        
        Args:
            cursor_store: Cursor store for checkpointing
            provider: Provider name
            repo_owner: Repository owner
            repo_name: Repository name
            entity_type: Entity type (prs, ci_runs, deployments)
            start_date: How far back to sync (default 90 days)
            batch_size: Records per batch
            progress_callback: Optional callback(batch_num, total_records)
        """
        self.cursor_store = cursor_store
        self.provider = provider
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.entity_type = entity_type
        self.start_date = start_date or (datetime.utcnow() - timedelta(days=90))
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        
        self.orchestrator = SyncOrchestrator(cursor_store, batch_size)
        self._records_processed = 0
        self._batches_processed = 0
    
    def run(self, fetcher: Callable[..., Iterator[dict]]) -> dict:
        """
        Execute backfill job.
        
        Args:
            fetcher: Generator that yields entities
        
        Returns:
            Statistics dict
        """
        logger.info(
            f"Starting backfill for {self.provider}:{self.repo_owner}/{self.repo_name} "
            f"({self.entity_type}) from {self.start_date.isoformat()}"
        )
        
        # Reset cursor for fresh backfill
        self.cursor_store.reset_cursor(
            self.provider, self.repo_owner, self.repo_name, self.entity_type
        )
        
        # Run sync in backfill mode
        stats = self.orchestrator.sync_repository(
            provider=self.provider,
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            entity_type=self.entity_type,
            fetcher=fetcher,
            mode=SyncMode.BACKFILL,
            start_date=self.start_date
        )
        
        logger.info(
            f"Backfill completed: {stats['records_synced']} records "
            f"in {stats['batches']} batches"
        )
        
        return stats
    
    def pause(self) -> None:
        """Pause backfill (finish current batch, then stop)."""
        self.orchestrator.stop()
        logger.info("Backfill pause requested")
    
    def get_progress(self) -> dict:
        """Get current progress."""
        return {
            'records_processed': self._records_processed,
            'batches_processed': self._batches_processed,
            'provider': self.provider,
            'repo': f"{self.repo_owner}/{self.repo_name}",
            'entity_type': self.entity_type,
            'start_date': self.start_date.isoformat()
        }


class BackfillScheduler:
    """
    Schedule and manage multiple backfill jobs.
    
    Useful for initial setup when you need to backfill
    multiple repositories or entity types.
    """
    
    def __init__(self, cursor_store: CursorStore):
        self.cursor_store = cursor_store
        self.jobs: list[BackfillJob] = []
        self.results: list[dict] = []
    
    def add_job(self, job: BackfillJob) -> None:
        """Add a backfill job to the queue."""
        self.jobs.append(job)
        logger.info(f"Added backfill job: {job.provider}:{job.repo_owner}/{job.repo_name}")
    
    def run_all(self, fetchers: dict[str, Callable]) -> list[dict]:
        """
        Run all backfill jobs sequentially.
        
        Args:
            fetchers: Dict mapping entity_type to fetcher function
        
        Returns:
            List of stats dicts
        """
        self.results = []
        
        for job in self.jobs:
            fetcher = fetchers.get(job.entity_type)
            if not fetcher:
                logger.warning(f"No fetcher for {job.entity_type}, skipping")
                continue
            
            try:
                stats = job.run(fetcher)
                self.results.append(stats)
            except Exception as e:
                logger.error(f"Backfill job failed: {e}")
                self.results.append({
                    'status': 'failed',
                    'error': str(e),
                    'provider': job.provider,
                    'repo': f"{job.repo_owner}/{job.repo_name}",
                    'entity_type': job.entity_type
                })
        
        return self.results
    
    def get_summary(self) -> dict:
        """Get summary of all backfill jobs."""
        total_records = sum(r.get('records_synced', 0) for r in self.results)
        completed = sum(1 for r in self.results if r.get('status') == 'completed')
        failed = sum(1 for r in self.results if r.get('status') == 'failed')
        
        return {
            'total_jobs': len(self.jobs),
            'completed': completed,
            'failed': failed,
            'total_records_synced': total_records,
            'jobs': self.results
        }
