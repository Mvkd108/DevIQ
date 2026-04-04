"""
Code Complexity Analyzer for DevHouse26.

This module analyzes code complexity at the AST level for multiple languages.
Designed to run locally and store results in Supabase.

Supported Languages:
- Python (ast module)
- JavaScript/TypeScript (esprima or tree-sitter)
- Java (tree-sitter-java)
- Go (tree-sitter-go)
- C/C++ (tree-sitter-c)

Metrics Calculated:
- Cyclomatic Complexity (McCabe)
- Cognitive Complexity
- Lines of Code
- Function/Method Count
- Maximum Nesting Depth
- Halstead Metrics (effort, difficulty)
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class ComplexityMetrics:
    """Code complexity metrics for a file or function."""
    
    file_path: str
    language: str
    
    # Basic metrics
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    
    # Complexity metrics
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    max_nesting_depth: int = 0
    
    # Function metrics
    function_count: int = 0
    average_function_length: float = 0.0
    max_function_complexity: int = 0
    
    # Halstead metrics
    halstead_volume: float = 0.0
    halstead_difficulty: float = 0.0
    halstead_effort: float = 0.0
    
    # Architectural impact
    imports_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    
    # Risk score (0-100)
    risk_score: float = 0.0
    
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CommitComplexityAnalysis:
    """Complexity analysis for a specific commit."""
    
    commit_id: str
    repository_name: str
    author: str
    timestamp: datetime
    
    # Files changed in this commit
    files_changed: int = 0
    total_complexity_delta: float = 0.0
    max_file_complexity: float = 0.0
    
    # Impact assessment
    architectural_impact: str = "low"  # low, medium, high, critical
    complexity_trend: str = "stable"  # decreased, stable, increased
    
    # Per-file breakdown
    file_metrics: List[ComplexityMetrics] = field(default_factory=list)
    
    calculated_at: datetime = field(default_factory=datetime.utcnow)


class PythonComplexityAnalyzer:
    """Analyze Python code complexity using AST."""
    
    def analyze_file(self, file_path: str, source_code: str) -> ComplexityMetrics:
        """Analyze a Python file's complexity."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return self._create_error_metrics(file_path, "python")
        
        metrics = ComplexityMetrics(
            file_path=file_path,
            language="python"
        )
        
        # Basic line metrics
        lines = source_code.split('\n')
        metrics.lines_of_code = len([l for l in lines if l.strip()])
        metrics.blank_lines = len([l for l in lines if not l.strip()])
        metrics.comment_lines = len([l for l in lines if l.strip().startswith('#')])
        
        # AST traversal for complexity
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        
        metrics.cyclomatic_complexity = visitor.cyclomatic_complexity
        metrics.cognitive_complexity = visitor.cognitive_complexity
        metrics.max_nesting_depth = visitor.max_nesting_depth
        metrics.function_count = visitor.function_count
        metrics.max_function_complexity = visitor.max_function_complexity
        
        if visitor.function_count > 0:
            metrics.average_function_length = visitor.total_function_lines / visitor.function_count
        
        # Import analysis
        metrics.imports_count = len(visitor.imports)
        metrics.dependencies = list(visitor.imports)
        
        # Halstead metrics approximation
        metrics.halstead_volume = self._calculate_halstead_volume(source_code)
        metrics.halstead_difficulty = metrics.cyclomatic_complexity * 0.5
        metrics.halstead_effort = metrics.halstead_volume * metrics.halstead_difficulty
        
        # Risk score calculation
        metrics.risk_score = self._calculate_risk_score(metrics)
        
        return metrics
    
    def _create_error_metrics(self, file_path: str, language: str) -> ComplexityMetrics:
        """Create empty metrics for files with syntax errors."""
        return ComplexityMetrics(
            file_path=file_path,
            language=language,
            risk_score=50  # Unknown = moderate risk
        )
    
    def _calculate_halstead_volume(self, source_code: str) -> float:
        """Approximate Halstead volume."""
        # Count operators and operands
        operators = len(re.findall(r'[\+\-\*/%=<>!&|^~]|\band\b|\bor\b|\bnot\b|\bis\b|\bin\b', source_code))
        operands = len(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', source_code))
        
        if operators + operands == 0:
            return 0.0
        
        vocabulary = operators + operands
        length = operators + operands
        
        # Volume = length * log2(vocabulary)
        import math
        return length * math.log2(max(vocabulary, 2))
    
    def _calculate_risk_score(self, metrics: ComplexityMetrics) -> float:
        """Calculate overall risk score (0-100)."""
        score = 0.0
        
        # Cyclomatic complexity weight
        if metrics.cyclomatic_complexity > 20:
            score += 30
        elif metrics.cyclomatic_complexity > 10:
            score += 20
        elif metrics.cyclomatic_complexity > 5:
            score += 10
        
        # Cognitive complexity weight
        if metrics.cognitive_complexity > 15:
            score += 25
        elif metrics.cognitive_complexity > 8:
            score += 15
        
        # File size weight
        if metrics.lines_of_code > 500:
            score += 20
        elif metrics.lines_of_code > 300:
            score += 10
        
        # Function complexity weight
        if metrics.max_function_complexity > 15:
            score += 15
        elif metrics.max_function_complexity > 10:
            score += 10
        
        # Nesting depth weight
        if metrics.max_nesting_depth > 4:
            score += 10
        
        return min(100, score)


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate complexity metrics."""
    
    def __init__(self):
        self.cyclomatic_complexity = 1  # Base complexity
        self.cognitive_complexity = 0
        self.max_nesting_depth = 0
        self.current_nesting = 0
        self.function_count = 0
        self.max_function_complexity = 0
        self.total_function_lines = 0
        self.imports = set()
    
    def visit_If(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += self.current_nesting + 1
        self._visit_nested(node)
    
    def visit_While(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += self.current_nesting + 1
        self._visit_nested(node)
    
    def visit_For(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += self.current_nesting + 1
        self._visit_nested(node)
    
    def visit_ExceptHandler(self, node):
        self.cyclomatic_complexity += 1
        self.cognitive_complexity += self.current_nesting + 1
        self._visit_nested(node)
    
    def visit_With(self, node):
        self._visit_nested(node)
    
    def visit_Try(self, node):
        self._visit_nested(node)
    
    def visit_FunctionDef(self, node):
        self._visit_function(node)
    
    def visit_AsyncFunctionDef(self, node):
        self._visit_function(node)
    
    def _visit_function(self, node):
        self.function_count += 1
        func_lines = node.end_lineno - node.lineno if node.end_lineno else 20
        self.total_function_lines += func_lines
        
        # Calculate function-specific complexity
        func_visitor = ComplexityVisitor()
        for child in ast.iter_child_nodes(node):
            func_visitor.visit(child)
        
        func_complexity = func_visitor.cyclomatic_complexity
        self.max_function_complexity = max(self.max_function_complexity, func_complexity)
        
        self._visit_nested(node)
    
    def _visit_nested(self, node):
        """Visit nested nodes with increased nesting level."""
        self.current_nesting += 1
        self.max_nesting_depth = max(self.max_nesting_depth, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)


class SimpleHeuristicAnalyzer:
    """Simple heuristic-based complexity for non-Python files."""
    
    LANGUAGE_PATTERNS = {
        'javascript': r'\.(js|jsx|ts|tsx|mjs)$',
        'java': r'\.(java)$',
        'go': r'\.(go)$',
        'cpp': r'\.(cpp|c|cc|h|hpp)$',
        'ruby': r'\.(rb)$',
        'php': r'\.(php)$',
    }
    
    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        for lang, pattern in self.LANGUAGE_PATTERNS.items():
            if re.search(pattern, file_path, re.IGNORECASE):
                return lang
        return 'unknown'
    
    def analyze_file(self, file_path: str, source_code: str) -> ComplexityMetrics:
        """Analyze file using heuristics."""
        language = self.detect_language(file_path)
        lines = source_code.split('\n')
        
        metrics = ComplexityMetrics(
            file_path=file_path,
            language=language
        )
        
        # Basic metrics
        metrics.lines_of_code = len([l for l in lines if l.strip()])
        metrics.blank_lines = len([l for l in lines if not l.strip()])
        metrics.comment_lines = self._count_comments(lines, language)
        
        # Heuristic complexity estimation
        metrics.cyclomatic_complexity = self._estimate_cyclomatic(lines, language)
        metrics.cognitive_complexity = metrics.cyclomatic_complexity * 0.8
        metrics.max_nesting_depth = self._estimate_nesting(lines, language)
        metrics.function_count = self._count_functions(source_code, language)
        
        if metrics.function_count > 0:
            metrics.average_function_length = metrics.lines_of_code / metrics.function_count
        
        # Import/dependency analysis
        metrics.imports_count, metrics.dependencies = self._count_imports(source_code, language)
        
        # Risk score
        metrics.risk_score = self._calculate_heuristic_risk(metrics)
        
        return metrics
    
    def _count_comments(self, lines: List[str], language: str) -> int:
        """Count comment lines by language."""
        comment_patterns = {
            'python': (r'#', r'"""|\'\'\''),
            'javascript': (r'//', r'/\*'),
            'java': (r'//', r'/\*'),
            'go': (r'//', r'/\*'),
            'cpp': (r'//', r'/\*'),
            'ruby': (r'#', r'=begin'),
            'php': (r'//|#', r'/\*'),
        }
        
        single, multi = comment_patterns.get(language, (r'#', r'\*'))
        count = 0
        in_multiline = False
        
        for line in lines:
            stripped = line.strip()
            if re.search(multi, stripped):
                in_multiline = not in_multiline
                count += 1
            elif in_multiline or re.match(single, stripped):
                count += 1
        
        return count
    
    def _estimate_cyclomatic(self, lines: List[str], language: str) -> int:
        """Estimate cyclomatic complexity from control structures."""
        # Common control structures across languages
        control_patterns = [
            r'\bif\b|\belse\s*if\b|\belif\b',
            r'\bfor\b|\bwhile\b',
            r'\bswitch\b|\bcase\b:',
            r'\bcatch\b|\bexcept\b',
            r'\b&&\b|\|\|',
            r'\?\s*:',  # ternary
        ]
        
        complexity = 1  # Base
        for line in lines:
            for pattern in control_patterns:
                complexity += len(re.findall(pattern, line, re.IGNORECASE))
        
        return complexity
    
    def _estimate_nesting(self, lines: List[str], language: str) -> int:
        """Estimate maximum nesting depth."""
        max_depth = 0
        current_depth = 0
        
        indent_pattern = r'^(\s+)'
        
        for line in lines:
            match = re.match(indent_pattern, line)
            if match:
                indent = len(match.group(1))
                # Assume 2 or 4 space indentation
                level = indent // 2 if indent % 4 != 0 else indent // 4
                current_depth = level
                max_depth = max(max_depth, current_depth)
        
        return max_depth
    
    def _count_functions(self, source_code: str, language: str) -> int:
        """Count function definitions by language."""
        patterns = {
            'python': r'\bdef\s+\w+\s*\(',
            'javascript': r'\bfunction\b|\b\w+\s*[=:]\s*\([^)]*\)\s*=>|\b\w+\s*\([^)]*\)\s*\{',
            'java': r'\b(public|private|protected|static|\s)+\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*\{',
            'go': r'\bfunc\s+\w+\s*\(',
            'cpp': r'\b[\w*:<>\s]+\s+\w+\s*\([^)]*\)\s*(const)?\s*\{',
        }
        
        pattern = patterns.get(language, r'\bfunction\b|\bdef\b')
        return len(re.findall(pattern, source_code))
    
    def _count_imports(self, source_code: str, language: str) -> Tuple[int, List[str]]:
        """Count imports and extract dependencies."""
        patterns = {
            'python': r'(?:from|import)\s+(\w+)',
            'javascript': r'(?:import\s+.*?\s+from\s+[\'"])(\S+)[\'"]|(?:require\s*\(\s*[\'"])(\S+)[\'"]',
            'java': r'import\s+(\w+)',
            'go': r'import\s+\(?\s*[\'"](\S+)[\'"]',
        }
        
        pattern = patterns.get(language, r'import\s+(\w+)')
        matches = re.findall(pattern, source_code)
        
        # Flatten tuple results from JavaScript pattern
        deps = []
        for match in matches:
            if isinstance(match, tuple):
                deps.extend([m for m in match if m])
            else:
                deps.append(match)
        
        return len(deps), list(set(deps))
    
    def _calculate_heuristic_risk(self, metrics: ComplexityMetrics) -> float:
        """Calculate risk score from heuristics."""
        score = 0.0
        
        # File size
        if metrics.lines_of_code > 500:
            score += 25
        elif metrics.lines_of_code > 300:
            score += 15
        elif metrics.lines_of_code > 100:
            score += 5
        
        # Cyclomatic
        if metrics.cyclomatic_complexity > 20:
            score += 25
        elif metrics.cyclomatic_complexity > 10:
            score += 15
        
        # Function count (too many = God object)
        if metrics.function_count > 20:
            score += 20
        elif metrics.function_count > 10:
            score += 10
        
        # Nesting
        if metrics.max_nesting_depth > 4:
            score += 15
        elif metrics.max_nesting_depth > 3:
            score += 10
        
        return min(100, score)


class CommitComplexityAnalyzer:
    """Analyze complexity changes in commits."""
    
    def __init__(self):
        self.python_analyzer = PythonComplexityAnalyzer()
        self.heuristic_analyzer = SimpleHeuristicAnalyzer()
    
    def analyze_commit(
        self,
        commit_id: str,
        repository_name: str,
        author: str,
        timestamp: datetime,
        changed_files: List[Dict[str, Any]]
    ) -> CommitComplexityAnalysis:
        """Analyze complexity for a commit's changed files."""
        
        analysis = CommitComplexityAnalysis(
            commit_id=commit_id,
            repository_name=repository_name,
            author=author,
            timestamp=timestamp,
            files_changed=len(changed_files)
        )
        
        total_complexity_before = 0
        total_complexity_after = 0
        
        for file_data in changed_files:
            file_path = file_data.get('path', '')
            source_after = file_data.get('content_after', '')
            source_before = file_data.get('content_before', '')
            
            # Analyze after state
            if file_path.endswith('.py'):
                metrics_after = self.python_analyzer.analyze_file(file_path, source_after)
            else:
                metrics_after = self.heuristic_analyzer.analyze_file(file_path, source_after)
            
            analysis.file_metrics.append(metrics_after)
            total_complexity_after += metrics_after.risk_score
            
            # Calculate delta if we have before state
            if source_before:
                if file_path.endswith('.py'):
                    metrics_before = self.python_analyzer.analyze_file(file_path, source_before)
                else:
                    metrics_before = self.heuristic_analyzer.analyze_file(file_path, source_before)
                
                total_complexity_before += metrics_before.risk_score
            
            analysis.max_file_complexity = max(
                analysis.max_file_complexity,
                metrics_after.risk_score
            )
        
        analysis.total_complexity_delta = total_complexity_after - total_complexity_before
        
        # Determine complexity trend
        if analysis.total_complexity_delta > 10:
            analysis.complexity_trend = "increased"
        elif analysis.total_complexity_delta < -10:
            analysis.complexity_trend = "decreased"
        else:
            analysis.complexity_trend = "stable"
        
        # Determine architectural impact
        if analysis.files_changed > 5 or analysis.max_file_complexity > 70:
            analysis.architectural_impact = "critical"
        elif analysis.files_changed > 3 or analysis.max_file_complexity > 50:
            analysis.architectural_impact = "high"
        elif analysis.files_changed > 1 or analysis.max_file_complexity > 30:
            analysis.architectural_impact = "medium"
        else:
            analysis.architectural_impact = "low"
        
        return analysis
    
    def analyze_batch(
        self,
        commits_data: List[Dict[str, Any]]
    ) -> List[CommitComplexityAnalysis]:
        """Analyze complexity for a batch of commits."""
        results = []
        
        for commit_data in commits_data:
            try:
                analysis = self.analyze_commit(
                    commit_id=commit_data['commit_id'],
                    repository_name=commit_data.get('repository_name', 'unknown'),
                    author=commit_data.get('author', 'unknown'),
                    timestamp=commit_data.get('timestamp', datetime.utcnow()),
                    changed_files=commit_data.get('changed_files', [])
                )
                results.append(analysis)
            except Exception as e:
                print(f"Error analyzing commit {commit_data.get('commit_id', 'unknown')}: {e}")
                continue
        
        return results


def format_complexity_for_storage(
    analysis: CommitComplexityAnalysis
) -> Dict[str, Any]:
    """Format complexity analysis for Supabase storage."""
    return {
        'commit_id': analysis.commit_id,
        'repository_name': analysis.repository_name,
        'author': analysis.author,
        'timestamp': analysis.timestamp.isoformat(),
        'files_changed': analysis.files_changed,
        'total_complexity_delta': analysis.total_complexity_delta,
        'max_file_complexity': analysis.max_file_complexity,
        'architectural_impact': analysis.architectural_impact,
        'complexity_trend': analysis.complexity_trend,
        'file_metrics': [
            {
                'file_path': m.file_path,
                'language': m.language,
                'lines_of_code': m.lines_of_code,
                'cyclomatic_complexity': m.cyclomatic_complexity,
                'cognitive_complexity': m.cognitive_complexity,
                'max_nesting_depth': m.max_nesting_depth,
                'function_count': m.function_count,
                'risk_score': m.risk_score,
                'dependencies': m.dependencies
            }
            for m in analysis.file_metrics
        ],
        'calculated_at': analysis.calculated_at.isoformat()
    }
