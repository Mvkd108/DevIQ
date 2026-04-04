"""
Canonical Developer Identity Resolution System.

This module provides conservative identity resolution across multiple sources
(git, Jira, GitHub, employee directory) to identify unique developers while
avoiding false positive merges.

Key principles:
- Never auto-merge identities with conflicting team/manager assignments
- Expose confidence scores and evidence for every resolution
- Flag ambiguous cases for manual review instead of guessing
- Support identity aliases from multiple sources

Example usage:
    resolver = IdentityResolver()
    
    # Resolve a developer from multiple source identities
    developer = resolver.resolve_identity(
        git_email="john.doe@company.com",
        git_name="John Doe",
        jira_assignee="john.doe",
        pr_author="jdoe123",
        employee_email="john.doe@company.com"
    )
    
    # Add an alias for an existing canonical identity
    resolver.add_alias(
        canonical_id="dev-123",
        source_type="github",
        source_value="johndoe-alt",
        confidence=0.95
    )
    
    # Find potential matches for a pattern
    matches = resolver.find_matches(email_pattern="*@company.com")
    
    # Detect ambiguous identity conflicts
    collisions = resolver.detect_collisions()
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Optional


class SourceType(Enum):
    """Source types for identity aliases."""

    GIT = "git"
    JIRA = "jira"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    EMPLOYEE_DIRECTORY = "employee_directory"
    SLACK = "slack"
    UNKNOWN = "unknown"


class MatchConfidence(Enum):
    """Confidence levels for identity matches."""

    EXACT = 0.95  # Exact email match
    HIGH = 0.85  # Multiple strong signals
    MEDIUM = 0.7  # Name similarity + domain match
    LOW = 0.4  # Name-only similarity
    SUSPICIOUS = 0.2  # Weak signal, needs review
    AMBIGUOUS = 0.0  # Conflicting signals, manual review required


@dataclass
class IdentityAlias:
    """An alias linking a source identity to a canonical developer."""

    source_type: SourceType
    source_value: str
    confidence: float
    added_at: str = field(default_factory=lambda: "")
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.added_at:
            from datetime import datetime, timezone

            self.added_at = datetime.now(timezone.utc).isoformat()


@dataclass
class CanonicalDeveloper:
    """A canonical developer identity representing a unique person.

    This is the result of identity resolution, representing a single
    developer across all their source system identities.
    """

    id: str  # Unique canonical ID
    primary_email: Optional[str] = None
    primary_name: Optional[str] = None
    department: Optional[str] = None
    team: Optional[str] = None
    manager_email: Optional[str] = None
    aliases: list[IdentityAlias] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: "")
    updated_at: str = field(default_factory=lambda: "")
    resolution_confidence: float = 0.0
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    merge_blocked_reason: Optional[str] = None

    def __post_init__(self):
        from datetime import datetime, timezone

        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def get_aliases_by_source(self, source_type: SourceType) -> list[IdentityAlias]:
        """Get all aliases for a specific source type."""
        return [a for a in self.aliases if a.source_type == source_type]

    def get_all_emails(self) -> set[str]:
        """Get all email addresses associated with this developer."""
        emails = set()
        if self.primary_email:
            emails.add(self.primary_email.lower())
        for alias in self.aliases:
            if "@" in alias.source_value:
                emails.add(alias.source_value.lower())
        return emails

    def get_all_names(self) -> set[str]:
        """Get all name variations associated with this developer."""
        names = set()
        if self.primary_name:
            names.add(self.primary_name.lower())
        for alias in self.aliases:
            # Skip obvious email addresses
            if "@" not in alias.source_value and "." in alias.source_value:
                names.add(alias.source_value.lower())
        return names


@dataclass
class IdentityMatch:
    """A potential match between source identities and a canonical developer."""

    canonical_id: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    conflicting_signals: list[str] = field(default_factory=list)
    match_type: str = ""  # "exact_email", "name_domain", "name_only", etc.


@dataclass
class IdentityCollision:
    """An ambiguous identity conflict requiring manual review."""

    collision_id: str
    identities: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    suggested_action: str = ""
    detected_at: str = field(default_factory=lambda: "")

    def __post_init__(self):
        from datetime import datetime, timezone

        if not self.detected_at:
            self.detected_at = datetime.now(timezone.utc).isoformat()


class IdentityResolver:
    """Main identity resolution engine.

    Implements conservative matching rules:
    - Exact email match = highest confidence (0.95)
    - Name similarity with email domain match = medium confidence (0.7)
    - Name-only similarity = low confidence (0.4)
    - Cross-source disagreement lowers confidence
    - Conflicting org mappings = mark ambiguous, don't auto-merge
    """

    def __init__(self, storage_provider: Any = None):
        """Initialize the identity resolver.

        Args:
            storage_provider: Optional storage backend for persisting identities.
                             If None, identities are stored in memory only.
        """
        self._developers: dict[str, CanonicalDeveloper] = {}
        self._email_index: dict[str, str] = {}  # email -> canonical_id
        self._alias_index: dict[tuple[SourceType, str], str] = {}  # (type, value) -> canonical_id
        self._storage = storage_provider
        self._collisions: list[IdentityCollision] = []
        self._next_id = 1

    def _generate_id(self) -> str:
        """Generate a unique canonical developer ID."""
        id_val = f"dev-{self._next_id:06d}"
        self._next_id += 1
        return id_val

    def _normalize_email(self, email: Optional[str]) -> Optional[str]:
        """Normalize email address for comparison."""
        if not email:
            return None
        email = email.strip().lower()
        # Remove common aliases (e.g., john+tag@example.com -> john@example.com)
        if "+" in email and "@" in email:
            local, domain = email.split("@", 1)
            local = local.split("+")[0]
            email = f"{local}@{domain}"
        return email

    def _normalize_name(self, name: Optional[str]) -> Optional[str]:
        """Normalize name for comparison."""
        if not name:
            return None
        # Remove extra whitespace, convert to lowercase
        name = " ".join(name.split()).lower()
        # Remove common suffixes/prefixes
        for suffix in ["(contractor)", "[contractor]", "- contractor", "(external)", "[external]"]:
            name = name.replace(suffix, "").strip()
        return name

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using SequenceMatcher."""
        n1 = self._normalize_name(name1) or ""
        n2 = self._normalize_name(name2) or ""
        if not n1 or not n2:
            return 0.0
        if n1 == n2:
            return 1.0
        # Handle "First Last" vs "Last, First" variations
        if "," in n1:
            parts1 = [p.strip() for p in n1.split(",")]
            n1 = f"{parts1[1]} {parts1[0]}" if len(parts1) > 1 else parts1[0]
        if "," in n2:
            parts2 = [p.strip() for p in n2.split(",")]
            n2 = f"{parts2[1]} {parts2[0]}" if len(parts2) > 1 else parts2[0]
        # Remove common middle initial variations
        n1_clean = re.sub(r"\s+[a-z]\.?\s+", " ", n1)
        n2_clean = re.sub(r"\s+[a-z]\.?\s+", " ", n2)
        # Calculate similarity
        similarity = SequenceMatcher(None, n1_clean, n2_clean).ratio()
        # Boost for exact word matches
        words1 = set(n1_clean.split())
        words2 = set(n2_clean.split())
        if words1 == words2:
            similarity = max(similarity, 0.9)
        return similarity

    def _extract_domain(self, email: Optional[str]) -> Optional[str]:
        """Extract domain from email address."""
        if not email or "@" not in email:
            return None
        return email.split("@")[1].lower()

    def _check_org_conflict(
        self,
        dev1: CanonicalDeveloper,
        team: Optional[str] = None,
        manager: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """Check if there's an organizational conflict.

        Returns:
            Tuple of (has_conflict, conflict_reason)
        """
        conflicts = []
        if team and dev1.team and team != dev1.team:
            conflicts.append(f"team mismatch: {dev1.team} vs {team}")
        if manager and dev1.manager_email:
            norm_mgr = self._normalize_email(manager)
            norm_existing = self._normalize_email(dev1.manager_email)
            if norm_mgr and norm_existing and norm_mgr != norm_existing:
                conflicts.append(f"manager mismatch")
        if conflicts:
            return True, "; ".join(conflicts)
        return False, None

    def resolve_identity(
        self,
        git_email: Optional[str] = None,
        git_name: Optional[str] = None,
        jira_assignee: Optional[str] = None,
        pr_author: Optional[str] = None,
        employee_email: Optional[str] = None,
        team: Optional[str] = None,
        manager_email: Optional[str] = None,
        department: Optional[str] = None,
    ) -> CanonicalDeveloper:
        """Resolve source identities to a canonical developer.

        This is the main entry point for identity resolution. It takes identity
        fragments from multiple source systems and either:
        1. Matches to an existing canonical developer
        2. Creates a new canonical developer
        3. Flags ambiguous cases for manual review

        Args:
            git_email: Email from git commits
            git_name: Name from git commits
            jira_assignee: Jira username/display name
            pr_author: GitHub/GitLab PR author username
            employee_email: Email from employee directory
            team: Team/organization assignment
            manager_email: Manager's email
            department: Department name

        Returns:
            CanonicalDeveloper with resolution details
        """
        # Collect all identity signals
        signals: dict[str, Any] = {
            "git_email": git_email,
            "git_name": git_name,
            "jira_assignee": jira_assignee,
            "pr_author": pr_author,
            "employee_email": employee_email,
        }

        # Find all potential matches
        matches: list[IdentityMatch] = []

        # Priority 1: Exact email matches (highest confidence)
        for email_field in ["git_email", "employee_email"]:
            email = signals.get(email_field)
            if email:
                norm_email = self._normalize_email(email)
                if norm_email and norm_email in self._email_index:
                    dev_id = self._email_index[norm_email]
                    matches.append(
                        IdentityMatch(
                            canonical_id=dev_id,
                            confidence=MatchConfidence.EXACT.value,
                            evidence=[f"Exact email match: {email_field}={email}"],
                            match_type="exact_email",
                        )
                    )

        # Priority 2: Name similarity with email domain match
        primary_email = employee_email or git_email
        primary_name = git_name
        primary_domain = self._extract_domain(primary_email)

        if primary_name and primary_domain:
            for dev_id, dev in self._developers.items():
                # Skip if already matched by email
                if any(m.canonical_id == dev_id for m in matches):
                    continue

                # Check name similarity
                for dev_name in dev.get_all_names():
                    name_sim = self._calculate_name_similarity(primary_name, dev_name)
                    if name_sim >= 0.8:  # High name similarity threshold
                        # Check domain match
                        dev_emails = dev.get_all_emails()
                        domain_match = any(
                            self._extract_domain(e) == primary_domain
                            for e in dev_emails
                        )
                        if domain_match:
                            matches.append(
                                IdentityMatch(
                                    canonical_id=dev_id,
                                    confidence=MatchConfidence.MEDIUM.value,
                                    evidence=[
                                        f"Name similarity: {name_sim:.2f}",
                                        f"Domain match: {primary_domain}",
                                    ],
                                    match_type="name_domain",
                                )
                            )
                            break

        # Priority 3: Name-only similarity (low confidence)
        if primary_name:
            for dev_id, dev in self._developers.items():
                # Skip if already matched
                if any(m.canonical_id == dev_id for m in matches):
                    continue

                for dev_name in dev.get_all_names():
                    name_sim = self._calculate_name_similarity(primary_name, dev_name)
                    if name_sim >= 0.85:  # Very high threshold for name-only
                        matches.append(
                            IdentityMatch(
                                canonical_id=dev_id,
                                confidence=MatchConfidence.LOW.value,
                                evidence=[f"High name similarity: {name_sim:.2f}"],
                                match_type="name_only",
                            )
                        )
                        break

        # Deduplicate matches by canonical_id, keeping highest confidence
        best_matches: dict[str, IdentityMatch] = {}
        for match in matches:
            if match.canonical_id not in best_matches:
                best_matches[match.canonical_id] = match
            elif match.confidence > best_matches[match.canonical_id].confidence:
                best_matches[match.canonical_id] = match

        # Decision logic
        if len(best_matches) == 0:
            # No matches - create new canonical developer
            return self._create_new_developer(
                git_email=git_email,
                git_name=git_name,
                jira_assignee=jira_assignee,
                pr_author=pr_author,
                employee_email=employee_email,
                team=team,
                manager_email=manager_email,
                department=department,
            )

        if len(best_matches) == 1:
            # Single match - verify no conflicts
            match = list(best_matches.values())[0]
            dev = self._developers[match.canonical_id]

            # Check for org conflicts
            has_conflict, conflict_reason = self._check_org_conflict(dev, team, manager_email)

            if has_conflict:
                # Create ambiguous entry, don't auto-merge
                collision = IdentityCollision(
                    collision_id=f"collision-{len(self._collisions) + 1:04d}",
                    identities=[
                        {"type": "existing", "developer": dev},
                        {"type": "incoming", "signals": signals, "team": team, "manager": manager_email},
                    ],
                    reason=f"Organizational conflict: {conflict_reason}",
                    suggested_action="Manual review required to resolve team/manager conflict",
                )
                self._collisions.append(collision)

                # Return existing but mark as ambiguous
                dev.is_ambiguous = True
                dev.ambiguity_reason = collision.reason
                return dev

            # Add aliases for new signals
            self._add_aliases_for_match(dev, signals, match.confidence, match.evidence)

            # Update developer info if provided
            if team and not dev.team:
                dev.team = team
            if manager_email and not dev.manager_email:
                dev.manager_email = manager_email
            if department and not dev.department:
                dev.department = department

            from datetime import datetime, timezone

            dev.updated_at = datetime.now(timezone.utc).isoformat()
            dev.resolution_confidence = match.confidence

            return dev

        # Multiple matches - ambiguous case
        if len(best_matches) > 1:
            # Check if all have same team/manager (might be legitimate duplicates)
            matched_devs = [self._developers[m.canonical_id] for m in best_matches.values()]
            teams = {d.team for d in matched_devs if d.team}
            managers = {d.manager_email for d in matched_devs if d.manager_email}

            if len(teams) <= 1 and len(managers) <= 1:
                # Same org context - might be same person with multiple accounts
                # Pick highest confidence match
                best_match = max(best_matches.values(), key=lambda m: m.confidence)
                dev = self._developers[best_match.canonical_id]

                # Add note about potential duplicate
                dev.ambiguity_reason = f"Multiple identity matches found: {', '.join(best_matches.keys())}"

                # Add aliases from other matches
                for match in best_matches.values():
                    if match.canonical_id != best_match.canonical_id:
                        self._add_aliases_for_match(
                            dev, signals, match.confidence * 0.8,  # Lower confidence for secondary matches
                            match.evidence + ["Secondary match from ambiguous resolution"]
                        )

                return dev

            # Different org contexts - definitely ambiguous
            collision = IdentityCollision(
                collision_id=f"collision-{len(self._collisions) + 1:04d}",
                identities=[
                    {"type": "existing", "developer": d}
                    for d in matched_devs
                ] + [{"type": "incoming", "signals": signals, "team": team, "manager": manager_email}],
                reason=f"Multiple matching identities with different org contexts. Teams: {teams}, Managers: {managers}",
                suggested_action="Manual review required - possible duplicate person or name collision",
            )
            self._collisions.append(collision)

            # Return the highest confidence match but marked ambiguous
            best_match = max(best_matches.values(), key=lambda m: m.confidence)
            dev = self._developers[best_match.canonical_id]
            dev.is_ambiguous = True
            dev.ambiguity_reason = collision.reason
            dev.resolution_confidence = MatchConfidence.AMBIGUOUS.value

            return dev

        # Should not reach here, but return a new developer as fallback
        return self._create_new_developer(
            git_email=git_email,
            git_name=git_name,
            jira_assignee=jira_assignee,
            pr_author=pr_author,
            employee_email=employee_email,
            team=team,
            manager_email=manager_email,
            department=department,
        )

    def _create_new_developer(
        self,
        git_email: Optional[str] = None,
        git_name: Optional[str] = None,
        jira_assignee: Optional[str] = None,
        pr_author: Optional[str] = None,
        employee_email: Optional[str] = None,
        team: Optional[str] = None,
        manager_email: Optional[str] = None,
        department: Optional[str] = None,
    ) -> CanonicalDeveloper:
        """Create a new canonical developer from source signals."""
        dev_id = self._generate_id()

        # Determine primary email and name
        primary_email = employee_email or git_email
        primary_name = git_name

        dev = CanonicalDeveloper(
            id=dev_id,
            primary_email=primary_email,
            primary_name=primary_name,
            team=team,
            manager_email=manager_email,
            department=department,
            resolution_confidence=1.0,  # New identity is fully confident
        )

        # Add aliases for all source signals
        aliases: list[tuple[SourceType, Optional[str]]] = [
            (SourceType.GIT, git_email),
            (SourceType.GIT, git_name),
            (SourceType.JIRA, jira_assignee),
            (SourceType.GITHUB, pr_author),
            (SourceType.EMPLOYEE_DIRECTORY, employee_email),
        ]

        for source_type, value in aliases:
            if value:
                alias = IdentityAlias(
                    source_type=source_type,
                    source_value=value,
                    confidence=1.0,
                    evidence=["Primary identity source"],
                )
                dev.aliases.append(alias)
                self._alias_index[(source_type, value)] = dev_id

        # Index email for fast lookups
        if primary_email:
            norm_email = self._normalize_email(primary_email)
            if norm_email:
                self._email_index[norm_email] = dev_id

        self._developers[dev_id] = dev
        return dev

    def _add_aliases_for_match(
        self,
        dev: CanonicalDeveloper,
        signals: dict[str, Any],
        confidence: float,
        evidence: list[str],
    ) -> None:
        """Add aliases to an existing developer based on source signals."""
        source_mapping: dict[str, SourceType] = {
            "git_email": SourceType.GIT,
            "git_name": SourceType.GIT,
            "jira_assignee": SourceType.JIRA,
            "pr_author": SourceType.GITHUB,
            "employee_email": SourceType.EMPLOYEE_DIRECTORY,
        }

        for signal_key, value in signals.items():
            if not value:
                continue

            source_type = source_mapping.get(signal_key, SourceType.UNKNOWN)
            key = (source_type, value)

            # Check if alias already exists
            if key in self._alias_index:
                continue

            # Create new alias
            alias = IdentityAlias(
                source_type=source_type,
                source_value=value,
                confidence=confidence,
                evidence=evidence.copy(),
            )
            dev.aliases.append(alias)
            self._alias_index[key] = dev.id

            # Index email if applicable
            if "@" in value:
                norm_email = self._normalize_email(value)
                if norm_email:
                    self._email_index[norm_email] = dev.id

    def add_alias(
        self,
        canonical_id: str,
        source_type: SourceType | str,
        source_value: str,
        confidence: float,
        evidence: Optional[list[str]] = None,
    ) -> bool:
        """Add an alias to an existing canonical developer.

        Args:
            canonical_id: The canonical developer ID
            source_type: Type of source (SourceType enum or string)
            source_value: The identity value (email, username, etc.)
            confidence: Confidence score (0.0-1.0)
            evidence: Optional list of evidence strings

        Returns:
            True if alias was added, False if developer not found or alias exists
        """
        if canonical_id not in self._developers:
            return False

        # Normalize source_type
        if isinstance(source_type, str):
            try:
                source_type = SourceType(source_type.lower())
            except ValueError:
                source_type = SourceType.UNKNOWN

        key = (source_type, source_value)

        # Check if alias already exists
        if key in self._alias_index:
            return False

        dev = self._developers[canonical_id]

        alias = IdentityAlias(
            source_type=source_type,
            source_value=source_value,
            confidence=confidence,
            evidence=evidence or ["Manually added alias"],
        )

        dev.aliases.append(alias)
        self._alias_index[key] = canonical_id

        # Index email
        if "@" in source_value:
            norm_email = self._normalize_email(source_value)
            if norm_email:
                self._email_index[norm_email] = canonical_id

        from datetime import datetime, timezone

        dev.updated_at = datetime.now(timezone.utc).isoformat()

        return True

    def find_matches(
        self,
        email_pattern: Optional[str] = None,
        name_pattern: Optional[str] = None,
    ) -> list[CanonicalDeveloper]:
        """Find potential identity matches based on patterns.

        Args:
            email_pattern: Glob pattern for email matching (e.g., "*@company.com")
            name_pattern: Glob pattern for name matching (e.g., "John*")

        Returns:
            List of CanonicalDeveloper objects matching the patterns
        """
        matches: list[CanonicalDeveloper] = []
        matched_ids: set[str] = set()

        # Convert glob patterns to regex
        def glob_to_regex(pattern: str) -> re.Pattern:
            regex = pattern.replace("*", ".*").replace("?", ".")
            return re.compile(regex, re.IGNORECASE)

        if email_pattern:
            email_regex = glob_to_regex(email_pattern)
            for email, dev_id in self._email_index.items():
                if email_regex.match(email) and dev_id not in matched_ids:
                    matches.append(self._developers[dev_id])
                    matched_ids.add(dev_id)

            # Also check aliases
            for dev in self._developers.values():
                if dev.id in matched_ids:
                    continue
                for email in dev.get_all_emails():
                    if email_regex.match(email):
                        matches.append(dev)
                        matched_ids.add(dev.id)
                        break

        if name_pattern:
            name_regex = glob_to_regex(name_pattern)
            for dev in self._developers.values():
                if dev.id in matched_ids:
                    continue
                for name in dev.get_all_names():
                    if name_regex.match(name):
                        matches.append(dev)
                        matched_ids.add(dev.id)
                        break

        return matches

    def detect_collisions(self) -> list[IdentityCollision]:
        """Detect ambiguous identity conflicts requiring manual review.

        This scans for:
        1. Same email across different canonical developers
        2. Same name but different org assignments
        3. Conflicting manager assignments
        4. Stored ambiguous resolutions from resolve_identity()

        Returns:
            List of IdentityCollision objects describing conflicts
        """
        collisions: list[IdentityCollision] = list(self._collisions)

        # Check for email collisions
        email_to_devs: dict[str, list[str]] = {}
        for dev_id, dev in self._developers.items():
            for email in dev.get_all_emails():
                if email not in email_to_devs:
                    email_to_devs[email] = []
                email_to_devs[email].append(dev_id)

        for email, dev_ids in email_to_devs.items():
            if len(dev_ids) > 1:
                # Same email in multiple developers
                devs = [self._developers[did] for did in dev_ids]
                teams = {d.team for d in devs if d.team}
                managers = {d.manager_email for d in devs if d.manager_email}

                if len(teams) > 1 or len(managers) > 1:
                    collision = IdentityCollision(
                        collision_id=f"collision-{len(collisions) + 1:04d}",
                        identities=[{"type": "existing", "developer": d} for d in devs],
                        reason=f"Same email ({email}) across developers with different org contexts",
                        suggested_action="Merge identities if same person, or separate if different people sharing email",
                    )
                    collisions.append(collision)

        # Check for name collisions with different managers
        name_to_devs: dict[str, list[str]] = {}
        for dev_id, dev in self._developers.items():
            for name in dev.get_all_names():
                if name not in name_to_devs:
                    name_to_devs[name] = []
                name_to_devs[name].append(dev_id)

        for name, dev_ids in name_to_devs.items():
            if len(dev_ids) > 1:
                devs = [self._developers[did] for did in dev_ids]
                managers = {d.manager_email for d in devs if d.manager_email}

                if len(managers) > 1:
                    collision = IdentityCollision(
                        collision_id=f"collision-{len(collisions) + 1:04d}",
                        identities=[{"type": "existing", "developer": d} for d in devs],
                        reason=f"Same name ({name}) with different manager assignments",
                        suggested_action="Verify if same person moved teams, or different people with same name",
                    )
                    collisions.append(collision)

        return collisions

    def get_developer(self, canonical_id: str) -> Optional[CanonicalDeveloper]:
        """Get a canonical developer by ID."""
        return self._developers.get(canonical_id)

    def get_developer_by_email(self, email: str) -> Optional[CanonicalDeveloper]:
        """Get a canonical developer by email address."""
        norm_email = self._normalize_email(email)
        if norm_email and norm_email in self._email_index:
            return self._developers.get(self._email_index[norm_email])
        return None

    def get_developer_by_alias(
        self,
        source_type: SourceType | str,
        source_value: str,
    ) -> Optional[CanonicalDeveloper]:
        """Get a canonical developer by source alias."""
        if isinstance(source_type, str):
            try:
                source_type = SourceType(source_type.lower())
            except ValueError:
                source_type = SourceType.UNKNOWN

        key = (source_type, source_value)
        if key in self._alias_index:
            return self._developers.get(self._alias_index[key])
        return None

    def list_all_developers(self) -> list[CanonicalDeveloper]:
        """List all canonical developers."""
        return list(self._developers.values())

    def get_stats(self) -> dict[str, Any]:
        """Get resolver statistics."""
        return {
            "total_developers": len(self._developers),
            "total_aliases": len(self._alias_index),
            "indexed_emails": len(self._email_index),
            "pending_collisions": len(self._collisions),
            "ambiguous_developers": sum(1 for d in self._developers.values() if d.is_ambiguous),
        }


def create_resolver(storage_provider: Any = None) -> IdentityResolver:
    """Factory function to create an IdentityResolver instance.

    Args:
        storage_provider: Optional storage backend for persistence

    Returns:
        Configured IdentityResolver instance
    """
    return IdentityResolver(storage_provider)
