#!/usr/bin/env python3
"""
Local Code Complexity Runner for DevHouse26.

This script runs locally on your machine (not on Render) to analyze
code complexity and store results in Supabase.

Usage:
    python run_complexity_analysis.py

Features:
- Analyzes Python files with full AST parsing
- Analyzes other languages with heuristics
- Stores results in Supabase
- Can process historical commits or new ones
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_complexity_analyzer import (
    CommitComplexityAnalyzer,
    format_complexity_for_storage,
    PythonComplexityAnalyzer,
    SimpleHeuristicAnalyzer
)

# Try to import Supabase client
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    print("Warning: supabase-py not installed. Install with: pip install supabase")
    HAS_SUPABASE = False

# Try to import python-dotenv for local env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class SupabaseComplexityStore:
    """Store and retrieve complexity data from Supabase."""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        self.client: Optional[Client] = None
        
        if HAS_SUPABASE and self.supabase_url and self.supabase_key:
            self.client = create_client(self.supabase_url, self.supabase_key)
    
    def is_connected(self) -> bool:
        """Check if Supabase connection is available."""
        return self.client is not None
    
    def get_unanalyzed_commits(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch commits that haven't been analyzed yet."""
        if not self.client:
            print("ERROR: Supabase not connected")
            return []
        
        try:
            # Get commits from extension_events that don't have complexity analysis
            response = self.client.table("extension_events").select("*").limit(limit).execute()
            
            if not response.data:
                return []
            
            # Filter out commits that already have complexity analysis
            commit_ids = [row["commit_id"] for row in response.data if row.get("commit_id")]
            
            if not commit_ids:
                return []
            
            # Check which ones already have analysis
            existing_response = self.client.table("commit_complexity_analysis").select("commit_id").in_("commit_id", commit_ids).execute()
            existing_ids = {row["commit_id"] for row in (existing_response.data or [])}
            
            # Return only unanalyzed commits
            unanalyzed = [
                row for row in response.data 
                if row.get("commit_id") and row["commit_id"] not in existing_ids
            ]
            
            print(f"Found {len(unanalyzed)} unanalyzed commits out of {len(response.data)} total")
            return unanalyzed
            
        except Exception as e:
            print(f"ERROR fetching commits: {e}")
            return []
    
    def store_complexity_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """Store complexity analysis result."""
        if not self.client:
            print("ERROR: Supabase not connected")
            return False
        
        try:
            response = self.client.table("commit_complexity_analysis").upsert(analysis_data).execute()
            return True
        except Exception as e:
            print(f"ERROR storing analysis: {e}")
            return False
    
    def store_file_metrics(self, file_metrics: List[Dict[str, Any]]) -> bool:
        """Store file-level complexity metrics."""
        if not self.client:
            return False
        
        if not file_metrics:
            return True
        
        try:
            response = self.client.table("file_complexity_snapshots").upsert(file_metrics).execute()
            return True
        except Exception as e:
            print(f"ERROR storing file metrics: {e}")
            return False
    
    def get_commit_complexity(self, commit_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complexity analysis for a commit."""
        if not self.client:
            return None
        
        try:
            response = self.client.table("commit_complexity_analysis").select("*").eq("commit_id", commit_id).single().execute()
            return response.data
        except:
            return None


class MockFileProvider:
    """Mock file content provider for testing."""
    
    def get_file_content(self, repository: str, commit_id: str, file_path: str) -> str:
        """Mock function - in real implementation, fetch from Git API."""
        # For demo, generate synthetic code based on file extension
        if file_path.endswith('.py'):
            return self._generate_python_code(file_path)
        elif file_path.endswith('.js') or file_path.endswith('.ts'):
            return self._generate_js_code(file_path)
        else:
            return self._generate_generic_code(file_path)
    
    def _generate_python_code(self, file_path: str) -> str:
        """Generate synthetic Python code for complexity testing."""
        # Create code with varying complexity
        import random
        random.seed(file_path)  # Deterministic based on filename
        
        complexity_level = random.choice(['low', 'medium', 'high', 'critical'])
        
        if complexity_level == 'low':
            return '''
def simple_function(data):
    """Simple function with low complexity."""
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
'''
        elif complexity_level == 'medium':
            return '''
def process_data(data, options):
    """Medium complexity function."""
    results = []
    for item in data:
        if item.type == 'A':
            if item.value > 10:
                results.append(item.process())
            elif item.value > 5:
                results.append(item.partial())
        elif item.type == 'B':
            for sub in item.subitems:
                if sub.active:
                    results.append(sub)
    return results
'''
        elif complexity_level == 'high':
            return '''
def complex_processor(data, config, validator):
    """High complexity function."""
    results = []
    errors = []
    
    for batch in data.batches:
        if not batch.valid:
            continue
            
        for item in batch.items:
            try:
                if item.priority == 1:
                    if validator.check(item):
                        if config.fast_mode:
                            results.append(item.fast_process())
                        else:
                            for sub in item.subtasks:
                                if sub.ready and not sub.blocked:
                                    results.append(sub.execute())
                    else:
                        errors.append(item)
                elif item.priority == 2 and not config.skip_low:
                    results.append(item.slow_process())
            except Exception as e:
                if config.ignore_errors:
                    continue
                else:
                    raise
                    
    return results, errors
'''
        else:  # critical
            return '''
def mega_processor(inputs, config, validator, transformer, notifier):
    """Critical complexity - god function."""
    all_results = []
    all_errors = []
    processed_count = 0
    
    for input_batch in inputs:
        if not validator.validate_batch(input_batch):
            if config.strict_mode:
                raise ValueError(f"Invalid batch: {input_batch.id}")
            else:
                notifier.warn(f"Skipping invalid batch {input_batch.id}")
                continue
        
        for item in input_batch.items:
            if item.skip:
                continue
                
            try:
                transformed = transformer.transform(item)
                
                if transformed.priority == 1:
                    if config.enable_feature_x:
                        if transformed.has_subtasks:
                            for sub in transformed.subtasks:
                                if not sub.blocked:
                                    if sub.priority > 5:
                                        result = sub.critical_process()
                                    else:
                                        result = sub.normal_process()
                                    all_results.append(result)
                        else:
                            all_results.append(transformed.process())
                    else:
                        all_results.append(transformed.legacy_process())
                        
                elif transformed.priority == 2:
                    if not config.skip_secondary:
                        if validator.validate_secondary(transformed):
                            result = transformed.secondary_process()
                            all_results.append(result)
                        else:
                            all_errors.append(transformed)
                            
                elif transformed.priority >= 3:
                    if config.include_low_priority:
                        all_results.append(transformed.low_process())
                        
                processed_count += 1
                
            except Exception as e:
                if config.error_handler == 'ignore':
                    continue
                elif config.error_handler == 'log':
                    all_errors.append((item, str(e)))
                else:
                    notifier.error(f"Failed processing {item.id}: {e}")
                    raise
                    
    notifier.info(f"Processed {processed_count} items")
    return all_results, all_errors, processed_count
'''
    
    def _generate_js_code(self, file_path: str) -> str:
        """Generate synthetic JavaScript code."""
        return '''
function processData(data, options) {
    const results = [];
    const errors = [];
    
    for (const item of data) {
        try {
            if (item.type === 'user') {
                if (item.active) {
                    if (item.premium) {
                        results.push(processPremium(item));
                    } else {
                        results.push(processStandard(item));
                    }
                }
            } else if (item.type === 'admin') {
                results.push(processAdmin(item));
            }
        } catch (e) {
            errors.push({ item, error: e });
        }
    }
    
    return { results, errors };
}
'''
    
    def _generate_generic_code(self, file_path: str) -> str:
        """Generate generic code for other languages."""
        return '''
// Generic processing function
function process(items) {
    var results = [];
    
    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        
        if (item.valid) {
            if (item.type === "A") {
                results.push(handleA(item));
            } else {
                results.push(handleOther(item));
            }
        }
    }
    
    return results;
}
'''


def analyze_and_store(
    store: SupabaseComplexityStore,
    file_provider: MockFileProvider,
    batch_size: int = 50
):
    """Main function to analyze commits and store results."""
    print("=" * 60)
    print("DEVHOUSE26 - Code Complexity Analyzer")
    print("=" * 60)
    
    if not store.is_connected():
        print("\nERROR: Cannot connect to Supabase!")
        print("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file")
        print("\nExample .env file:")
        print("SUPABASE_URL=https://jkwubrrronkyfpmdlvwd.supabase.co")
        print("SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here")
        return False
    
    print("\n[OK] Connected to Supabase")
    
    # Initialize analyzer
    analyzer = CommitComplexityAnalyzer()
    
    # Fetch unanalyzed commits
    print(f"\nFetching up to {batch_size} unanalyzed commits...")
    commits = store.get_unanalyzed_commits(limit=batch_size)
    
    if not commits:
        print("\nNo new commits to analyze.")
        return True
    
    print(f"\nAnalyzing {len(commits)} commits...")
    
    success_count = 0
    error_count = 0
    
    for i, commit in enumerate(commits, 1):
        commit_id = commit.get("commit_id", "unknown")
        print(f"\n[{i}/{len(commits)}] Analyzing {commit_id[:8]}...", end=" ")
        
        try:
            # Create mock changed files (in real scenario, fetch from Git API)
            changed_files = [
                {
                    "path": commit.get("file_path", "src/main.py"),
                    "content_after": file_provider.get_file_content(
                        commit.get("repository_name", "unknown"),
                        commit_id,
                        commit.get("file_path", "src/main.py")
                    ),
                    "content_before": None
                }
            ]
            
            # Parse timestamp (Supabase returns strings)
            timestamp_str = commit.get("timestamp")
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.utcnow()
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
            else:
                timestamp = datetime.utcnow()
            
            # Run analysis
            analysis = analyzer.analyze_commit(
                commit_id=commit_id,
                repository_name=commit.get("repository_name", "unknown"),
                author=commit.get("author", "unknown"),
                timestamp=timestamp,
                changed_files=changed_files
            )
            
            # Format for storage
            analysis_data = format_complexity_for_storage(analysis)
            
            # Store in Supabase
            if store.store_complexity_analysis(analysis_data):
                # Also store file metrics
                file_metrics = [
                    {
                        "file_path": m.file_path,
                        "repository_name": analysis.repository_name,
                        "commit_id": commit_id,
                        "language": m.language,
                        "lines_of_code": m.lines_of_code,
                        "cyclomatic_complexity": m.cyclomatic_complexity,
                        "cognitive_complexity": m.cognitive_complexity,
                        "max_nesting_depth": m.max_nesting_depth,
                        "function_count": m.function_count,
                        "risk_score": m.risk_score,
                        "dependencies": m.dependencies,
                        "calculated_at": datetime.utcnow().isoformat()
                    }
                    for m in analysis.file_metrics
                ]
                
                store.store_file_metrics(file_metrics)
                
                print(f"[OK] Risk: {analysis.max_file_complexity:.0f}, Impact: {analysis.architectural_impact}")
                success_count += 1
            else:
                print("[FAIL] Failed to store")
                error_count += 1
                
        except Exception as e:
            print(f"[FAIL] Error: {e}")
            error_count += 1
            continue
    
    print("\n" + "=" * 60)
    print(f"Analysis Complete!")
    print(f"  Successful: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total Processed: {success_count + error_count}")
    print("=" * 60)
    
    return success_count > 0


def main():
    """Main entry point."""
    print("\nStarting DevHouse26 Code Complexity Analysis...\n")
    
    # Debug: Show what env vars are found
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    
    print(f"Environment check:")
    print(f"  SUPABASE_URL: {'Found' if supabase_url else 'NOT FOUND'}")
    print(f"  SUPABASE_SERVICE_KEY: {'Found' if supabase_key else 'NOT FOUND'}")
    print(f"  HAS_SUPABASE module: {HAS_SUPABASE}")
    print()
    
    # Initialize components
    store = SupabaseComplexityStore()
    file_provider = MockFileProvider()
    
    # Run analysis
    success = analyze_and_store(store, file_provider, batch_size=50)
    
    if success:
        print("\n[OK] Complexity analysis completed successfully!")
        print("\nNext steps:")
        print("  1. Check your dashboard - complexity data is now available")
        print("  2. Run this script periodically for new commits")
        print("  3. View high-complexity commits in Supabase:")
        print("     SELECT * FROM high_complexity_commits;")
        return 0
    else:
        print("\n[FAIL] Analysis failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
