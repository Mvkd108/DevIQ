"""
Developer Skill Profile Inference Module

Infers developer skills from commit history using heuristics:
- File path analysis (keywords -> skill tags)
- Commit message patterns
- Complexity metrics
- Recency weighting

Produces ranked skill vectors with confidence scores and evidence.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional


# Skill tag mappings from file paths and patterns
PATH_SKILL_MAPPINGS = {
    # Database skills
    "migration": "database_schema",
    "schema": "database_schema",
    "db/": "database_design",
    "sql": "database_queries",
    "postgres": "database_admin",
    "mongo": "database_design",
    "redis": "caching",
    "elasticsearch": "search",
    
    # API/Backend skills
    "api": "api_design",
    "endpoint": "api_development",
    "controller": "backend_development",
    "service": "service_architecture",
    "middleware": "backend_development",
    "auth": "security",
    "oauth": "security",
    "jwt": "security",
    
    # Frontend skills
    "component": "frontend_development",
    "ui": "frontend_development",
    "react": "react_development",
    "vue": "vue_development",
    "angular": "angular_development",
    "css": "styling",
    "scss": "styling",
    "html": "markup",
    "dom": "frontend_development",
    
    # DevOps/Infrastructure
    "docker": "containerization",
    "k8s": "kubernetes",
    "terraform": "infrastructure",
    "ansible": "automation",
    "ci": "ci_cd",
    "cd": "ci_cd",
    "pipeline": "ci_cd",
    "github_actions": "ci_cd",
    "jenkins": "ci_cd",
    "deploy": "deployment",
    "helm": "kubernetes",
    
    # Testing
    "test": "testing",
    "spec": "testing",
    "jest": "testing",
    "cypress": "e2e_testing",
    "selenium": "e2e_testing",
    "unit": "unit_testing",
    "integration": "integration_testing",
    
    # Performance/Optimization
    "perf": "performance_tuning",
    "optimize": "performance_tuning",
    "cache": "caching",
    "memory": "memory_optimization",
    "bundle": "build_optimization",
    "webpack": "build_tools",
    
    # Debugging/Maintenance
    "fix": "debugging",
    "bug": "debugging",
    "hotfix": "debugging",
    "patch": "maintenance",
    "refactor": "code_quality",
    "clean": "code_quality",
}

# Commit message patterns -> skills
MESSAGE_SKILL_PATTERNS = {
    "fix": "debugging",
    "bugfix": "debugging",
    "debug": "debugging",
    "hotfix": "debugging",
    "optimize": "performance_tuning",
    "performance": "performance_tuning",
    "refactor": "code_quality",
    "cleanup": "code_quality",
    "test": "testing",
    "add test": "testing",
    "implement": "feature_development",
    "feature": "feature_development",
    "security": "security",
    "auth": "security",
    "migrate": "database_schema",
    "upgrade": "maintenance",
    "update": "maintenance",
    "document": "documentation",
    "readme": "documentation",
}


@dataclass
class SkillEvidence:
    """Evidence for a skill from a specific commit."""
    commit_id: str
    timestamp: datetime
    impact_score: float  # 0-1 based on complexity and churn
    file_paths: list[str]
    detection_method: str  # 'path_keyword', 'message_pattern', 'complexity'


@dataclass
class SkillScore:
    """Scored skill with full evidence."""
    skill_tag: str
    skill_category: str
    total_score: float  # 0-100
    confidence_score: float  # 0-1
    confidence_label: str  # 'high', 'medium', 'low'
    
    # Component scores
    frequency_score: float  # How often used
    recency_score: float  # Weighted by recency
    complexity_score: float  # Complexity of related work
    churn_score: float  # Code churn contribution
    
    # Evidence
    evidence_commits: list[SkillEvidence] = field(default_factory=list)
    evidence_count: int = 0
    last_commit_at: Optional[datetime] = None
    calculated_at: datetime = field(default_factory=datetime.utcnow)


class SkillProfiler:
    """
    Infers developer skills from commit history.
    
    Uses heuristics to map file paths, commit messages, and complexity
    metrics to high-level skill tags with confidence scoring.
    """
    
    def __init__(self, recency_half_life_days: int = 30):
        """
        Initialize skill profiler.
        
        Args:
            recency_half_life_days: Days for recency decay half-life
        """
        self.recency_half_life = recency_half_life_days
        self.path_mappings = PATH_SKILL_MAPPINGS
        self.message_patterns = MESSAGE_SKILL_PATTERNS
    
    def profile_developer(
        self,
        developer_id: str,
        commits: list[dict[str, Any]],
        developer_name: Optional[str] = None,
        developer_email: Optional[str] = None,
    ) -> list[SkillScore]:
        """
        Generate skill profile from developer's commit history.
        
        Args:
            developer_id: Developer identifier
            commits: List of commit dictionaries with files, message, timestamp, etc.
            developer_name: Optional display name
            developer_email: Optional email
            
        Returns:
            List of SkillScore objects ranked by total_score
        """
        # Collect skill evidence from all commits
        skill_evidence: dict[str, list[SkillEvidence]] = defaultdict(list)
        
        for commit in commits:
            commit_skills = self._extract_commit_skills(commit)
            for skill_tag, evidence in commit_skills.items():
                skill_evidence[skill_tag].append(evidence)
        
        # Calculate scores for each skill
        scores: list[SkillScore] = []
        now = datetime.utcnow()
        
        for skill_tag, evidence_list in skill_evidence.items():
            score = self._calculate_skill_score(skill_tag, evidence_list, now)
            scores.append(score)
        
        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        return scores
    
    def _extract_commit_skills(
        self,
        commit: dict[str, Any],
    ) -> dict[str, SkillEvidence]:
        """
        Extract skill evidence from a single commit.
        
        Returns:
            Mapping of skill_tag -> SkillEvidence
        """
        detected_skills: dict[str, SkillEvidence] = {}
        
        commit_id = commit.get("commit_id", str(uuid.uuid4())[:8])
        timestamp = self._parse_timestamp(commit.get("timestamp"))
        files = commit.get("files", [])
        message = commit.get("message", "").lower()
        total_changes = commit.get("total_changes", 0)
        
        # Calculate impact score based on changes
        impact_score = min(1.0, total_changes / 100)  # Cap at 100 changes
        
        # Detect from file paths
        file_paths: list[str] = []
        if isinstance(files, list):
            for file_info in files:
                if isinstance(file_info, dict):
                    path = file_info.get("path", "")
                    file_paths.append(path)
                    
                    # Check for path keywords
                    for keyword, skill in self.path_mappings.items():
                        if keyword in path.lower():
                            if skill not in detected_skills:
                                detected_skills[skill] = SkillEvidence(
                                    commit_id=commit_id,
                                    timestamp=timestamp,
                                    impact_score=impact_score,
                                    file_paths=[path],
                                    detection_method="path_keyword",
                                )
        
        # Detect from commit message
        for pattern, skill in self.message_patterns.items():
            if pattern in message:
                if skill not in detected_skills:
                    detected_skills[skill] = SkillEvidence(
                        commit_id=commit_id,
                        timestamp=timestamp,
                        impact_score=impact_score * 0.8,  # Slightly lower weight
                        file_paths=file_paths,
                        detection_method="message_pattern",
                    )
        
        return detected_skills
    
    def _calculate_skill_score(
        self,
        skill_tag: str,
        evidence_list: list[SkillEvidence],
        reference_time: datetime,
    ) -> SkillScore:
        """
        Calculate comprehensive skill score from evidence.
        """
        if not evidence_list:
            return SkillScore(
                skill_tag=skill_tag,
                skill_category=self._categorize_skill(skill_tag),
                total_score=0,
                confidence_score=0,
                confidence_label="low",
                frequency_score=0,
                recency_score=0,
                complexity_score=0,
                churn_score=0,
            )
        
        # Frequency: raw count (normalized)
        frequency_score = min(100, len(evidence_list) * 10)
        
        # Recency: weighted by how recent
        recency_score = self._calculate_recency_score(evidence_list, reference_time)
        
        # Complexity: average impact score
        complexity_score = sum(e.impact_score for e in evidence_list) / len(evidence_list) * 100
        
        # Churn: total impact
        churn_score = min(100, sum(e.impact_score for e in evidence_list) * 20)
        
        # Total score: weighted combination
        total_score = (
            frequency_score * 0.25 +
            recency_score * 0.30 +
            complexity_score * 0.25 +
            churn_score * 0.20
        )
        
        # Confidence based on evidence quantity and consistency
        confidence_score = min(1.0, len(evidence_list) / 10)  # Max at 10+ commits
        if len(evidence_list) >= 5:
            confidence_label = "high"
        elif len(evidence_list) >= 3:
            confidence_label = "medium"
        else:
            confidence_label = "low"
        
        # Get last commit timestamp
        last_commit = max(
            (e.timestamp for e in evidence_list if e.timestamp),
            default=None
        )
        
        return SkillScore(
            skill_tag=skill_tag,
            skill_category=self._categorize_skill(skill_tag),
            total_score=round(total_score, 2),
            confidence_score=round(confidence_score, 2),
            confidence_label=confidence_label,
            frequency_score=round(frequency_score, 2),
            recency_score=round(recency_score, 2),
            complexity_score=round(complexity_score, 2),
            churn_score=round(churn_score, 2),
            evidence_commits=evidence_list,
            evidence_count=len(evidence_list),
            last_commit_at=last_commit,
        )
    
    def _calculate_recency_score(
        self,
        evidence_list: list[SkillEvidence],
        reference_time: datetime,
    ) -> float:
        """Calculate recency-weighted score using exponential decay."""
        if not evidence_list:
            return 0.0
        
        total_weight = 0.0
        for evidence in evidence_list:
            if not evidence.timestamp:
                continue
            
            days_ago = (reference_time - evidence.timestamp).days
            # Exponential decay: weight = 0.5^(days/half_life)
            weight = 0.5 ** (days_ago / self.recency_half_life)
            total_weight += weight
        
        # Normalize to 0-100 scale
        return min(100, total_weight * 25)
    
    def _categorize_skill(self, skill_tag: str) -> str:
        """Categorize skill into high-level category."""
        domain_skills = {"database_design", "database_schema", "database_queries", "database_admin"}
        process_skills = {"testing", "ci_cd", "documentation", "debugging", "maintenance"}
        
        if skill_tag in domain_skills:
            return "domain"
        elif skill_tag in process_skills:
            return "process"
        else:
            return "technical"
    
    def _parse_timestamp(self, value: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                pass
        return datetime.utcnow()
    
    def find_similar_experts(
        self,
        target_skills: list[str],
        all_profiles: dict[str, list[SkillScore]],
        exclude_developer_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Find developers with similar skill profiles.
        
        Returns:
            List of (developer_id, similarity_score) tuples sorted by score
        """
        matches: list[tuple[str, float]] = []
        
        for dev_id, skills in all_profiles.items():
            if dev_id == exclude_developer_id:
                continue
            
            # Calculate overlap with target skills
            dev_skill_set = {s.skill_tag for s in skills}
            overlap = len(set(target_skills) & dev_skill_set)
            similarity = overlap / len(target_skills) if target_skills else 0
            
            if similarity > 0.3:  # At least 30% overlap
                matches.append((dev_id, similarity))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]
