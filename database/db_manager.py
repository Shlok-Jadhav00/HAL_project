"""
AEIA — SQLite Database Connection and Session Handling

This is the ONLY module that executes raw SQL. GUI panels and core/ modules
call methods on DatabaseManager instead of writing SQL themselves
(code_hygiene_guide.md §1, technical_design.md Part B).

Schema: database/schema.sql (11 tables, applied on first run).
No PyQt5 imports allowed in this module.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.models import (
    AnomalyRecord,
    AppSettingRecord,
    DatasetRecord,
    InsightRecord,
    PatternRecord,
    RecommendationRecord,
    ReportRecord,
    RuleDefinitionRecord,
    RuleMatchRecord,
    SessionRecord,
    StatisticalResultRecord,
)

logger = logging.getLogger('aeia.database')


class DatabaseManager:
    """Manages the SQLite database for AEIA.

    Responsibilities:
    - Schema initialization from database/schema.sql
    - CRUD operations for all 11 tables
    - Settings synchronization between settings.json and the app_settings table

    Usage:
        db = DatabaseManager('/path/to/aeia.db')
        db.initialize_schema()
        dataset_id = db.insert_dataset('test.csv', '/data/test.csv', 'CSV', 100, 5)
    """

    def __init__(self, db_path: str):
        """
        Args:
            db_path: Absolute path to the SQLite database file (aeia.db).
                     The parent directory must exist.
        """
        self._db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def get_connection(self) -> sqlite3.Connection:
        """Return a persistent SQLite connection, creating it if needed.

        Enables WAL mode for better concurrent read performance and
        foreign key enforcement.
        """
        if self._connection is None:
            # Ensure the parent directory exists
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._connection = sqlite3.connect(self._db_path)
            self._connection.execute('PRAGMA journal_mode=WAL')
            self._connection.execute('PRAGMA foreign_keys=ON')
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self):
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # ------------------------------------------------------------------
    # Schema initialization
    # ------------------------------------------------------------------

    def initialize_schema(self):
        """Apply database/schema.sql if the tables don't already exist.

        The schema file is located relative to this module's directory
        (during development) or via sys._MEIPASS (when packaged).
        """
        conn = self.get_connection()

        # Check if tables already exist (use 'datasets' as the canary)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='datasets'"
        )
        if cursor.fetchone() is not None:
            logger.info('Database schema already initialized.')
            return

        # Find schema.sql
        schema_path = self._find_schema_file()
        if schema_path is None:
            raise FileNotFoundError(
                'Cannot find database/schema.sql. Ensure the file exists in '
                'the project directory or is bundled with PyInstaller.'
            )

        logger.info('Applying schema from: %s', schema_path)
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()
        logger.info('Database schema initialized successfully.')

    def _find_schema_file(self) -> Optional[str]:
        """Locate schema.sql — handles both dev and packaged modes."""
        import sys

        if getattr(sys, 'frozen', False):
            # PyInstaller bundle
            candidate = os.path.join(sys._MEIPASS, 'database', 'schema.sql')
        else:
            # Development — schema.sql is in the same directory as this module
            candidate = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'schema.sql'
            )

        return candidate if os.path.isfile(candidate) else None

    # ------------------------------------------------------------------
    # Table 1: datasets (FR-010)
    # ------------------------------------------------------------------

    def insert_dataset(self, filename: str, source_path: str,
                       file_type: str, row_count: int,
                       column_count: int) -> int:
        """Insert a new dataset metadata record.

        FR-010: Store dataset metadata (filename, path, row count, column
        count, import timestamp) as a new datasets record.

        Returns:
            The auto-generated dataset_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO datasets (filename, source_path, file_type, '
            'row_count, column_count) VALUES (?, ?, ?, ?, ?)',
            (filename, source_path, file_type, row_count, column_count)
        )
        conn.commit()
        return cursor.lastrowid

    def get_dataset(self, dataset_id: int) -> Optional[DatasetRecord]:
        """Retrieve a single dataset record by ID."""
        conn = self.get_connection()
        row = conn.execute(
            'SELECT * FROM datasets WHERE dataset_id = ?', (dataset_id,)
        ).fetchone()
        return self._row_to_dataset(row) if row else None

    def list_datasets(self) -> List[DatasetRecord]:
        """Retrieve all dataset records, ordered by import date descending."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM datasets ORDER BY imported_on DESC'
        ).fetchall()
        return [self._row_to_dataset(r) for r in rows]

    @staticmethod
    def _row_to_dataset(row: sqlite3.Row) -> DatasetRecord:
        return DatasetRecord(
            dataset_id=row['dataset_id'],
            filename=row['filename'],
            source_path=row['source_path'],
            file_type=row['file_type'],
            row_count=row['row_count'],
            column_count=row['column_count'],
            imported_on=row['imported_on'],
        )

    # ------------------------------------------------------------------
    # Table 2: sessions (FR-098)
    # ------------------------------------------------------------------

    def create_session(self, dataset_id: int) -> int:
        """Create a new analysis session for a dataset.

        FR-098: Persist a record of every completed session.

        Returns:
            The auto-generated session_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO sessions (dataset_id) VALUES (?)', (dataset_id,)
        )
        conn.commit()
        return cursor.lastrowid

    def update_session(self, session_id: int, status: str,
                       findings_count: int,
                       completed_on: Optional[str] = None):
        """Update a session's status and findings count.

        Args:
            status: 'In Progress', 'Completed', or 'Failed'.
            completed_on: ISO timestamp; if None, uses current time when
                          status is 'Completed'.
        """
        if completed_on is None and status == 'Completed':
            completed_on = datetime.now().isoformat()
        conn = self.get_connection()
        conn.execute(
            'UPDATE sessions SET status = ?, findings_count = ?, '
            'completed_on = ? WHERE session_id = ?',
            (status, findings_count, completed_on, session_id)
        )
        conn.commit()

    def get_session(self, session_id: int) -> Optional[SessionRecord]:
        """Retrieve a single session record by ID."""
        conn = self.get_connection()
        row = conn.execute(
            'SELECT * FROM sessions WHERE session_id = ?', (session_id,)
        ).fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(self) -> List[SessionRecord]:
        """Retrieve all sessions, most recent first (FR-099)."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM sessions ORDER BY started_on DESC'
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def delete_session(self, session_id: int):
        """Delete a session and all its cascaded child records (FR-102)."""
        conn = self.get_connection()
        conn.execute(
            'DELETE FROM sessions WHERE session_id = ?', (session_id,)
        )
        conn.commit()

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            session_id=row['session_id'],
            dataset_id=row['dataset_id'],
            started_on=row['started_on'],
            completed_on=row['completed_on'],
            findings_count=row['findings_count'],
            status=row['status'],
        )

    # ------------------------------------------------------------------
    # Table 3: statistical_results (FR-021 – FR-028)
    # ------------------------------------------------------------------

    def insert_statistical_result(self, session_id: int, column_name: str,
                                  stats: Dict[str, Any]) -> int:
        """Insert per-column statistics for a session.

        Args:
            stats: Dict with keys matching the column names in the table:
                   mean, median, mode, std_dev, variance, min_value,
                   max_value, q1, q3, iqr, trend_slope, extra_json.

        Returns:
            The auto-generated result_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO statistical_results '
            '(session_id, column_name, mean, median, mode, std_dev, variance, '
            'min_value, max_value, q1, q3, iqr, trend_slope, extra_json) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                session_id, column_name,
                stats.get('mean'), stats.get('median'), stats.get('mode'),
                stats.get('std_dev'), stats.get('variance'),
                stats.get('min_value'), stats.get('max_value'),
                stats.get('q1'), stats.get('q3'), stats.get('iqr'),
                stats.get('trend_slope'), stats.get('extra_json'),
            )
        )
        conn.commit()
        return cursor.lastrowid

    def get_statistical_results(self, session_id: int) -> List[StatisticalResultRecord]:
        """Retrieve all statistical results for a session."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM statistical_results WHERE session_id = ? '
            'ORDER BY column_name',
            (session_id,)
        ).fetchall()
        return [self._row_to_stat(r) for r in rows]

    @staticmethod
    def _row_to_stat(row: sqlite3.Row) -> StatisticalResultRecord:
        return StatisticalResultRecord(
            result_id=row['result_id'],
            session_id=row['session_id'],
            column_name=row['column_name'],
            mean=row['mean'],
            median=row['median'],
            mode=row['mode'],
            std_dev=row['std_dev'],
            variance=row['variance'],
            min_value=row['min_value'],
            max_value=row['max_value'],
            q1=row['q1'],
            q3=row['q3'],
            iqr=row['iqr'],
            trend_slope=row['trend_slope'],
            extra_json=row['extra_json'],
        )

    # ------------------------------------------------------------------
    # Table 4: anomalies (FR-031 – FR-039)
    # ------------------------------------------------------------------

    def insert_anomaly(self, session_id: int, column_name: str,
                       row_reference: int, method: str,
                       severity: str, value: Optional[float] = None) -> int:
        """Insert a detected anomaly.

        FR-035: List every detected anomaly with its row reference,
        column(s), and detection method.

        Returns:
            The auto-generated anomaly_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO anomalies '
            '(session_id, column_name, row_reference, method, severity, value) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (session_id, column_name, row_reference, method, severity, value)
        )
        conn.commit()
        return cursor.lastrowid

    def get_anomalies(self, session_id: int,
                      include_false_positives: bool = True) -> List[AnomalyRecord]:
        """Retrieve anomalies for a session.

        Args:
            include_false_positives: If False, excludes anomalies marked as
                                     false positives (FR-039).
        """
        conn = self.get_connection()
        query = 'SELECT * FROM anomalies WHERE session_id = ?'
        params: list = [session_id]
        if not include_false_positives:
            query += ' AND is_false_positive = 0'
        query += ' ORDER BY anomaly_id'
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_anomaly(r) for r in rows]

    def update_anomaly_false_positive(self, anomaly_id: int,
                                      is_false_positive: bool):
        """Mark or unmark an anomaly as a false positive (FR-039)."""
        conn = self.get_connection()
        conn.execute(
            'UPDATE anomalies SET is_false_positive = ? WHERE anomaly_id = ?',
            (is_false_positive, anomaly_id)
        )
        conn.commit()

    @staticmethod
    def _row_to_anomaly(row: sqlite3.Row) -> AnomalyRecord:
        return AnomalyRecord(
            anomaly_id=row['anomaly_id'],
            session_id=row['session_id'],
            column_name=row['column_name'],
            row_reference=row['row_reference'],
            method=row['method'],
            severity=row['severity'],
            value=row['value'],
            is_false_positive=bool(row['is_false_positive']),
        )

    # ------------------------------------------------------------------
    # Table 5: patterns (FR-036, FR-025, FR-026)
    # ------------------------------------------------------------------

    def insert_pattern(self, session_id: int, pattern_type: str,
                       columns_involved: str,
                       description: Optional[str] = None,
                       strength: Optional[float] = None) -> int:
        """Insert a detected pattern (trend, correlation, etc.).

        Returns:
            The auto-generated pattern_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO patterns '
            '(session_id, pattern_type, columns_involved, description, strength) '
            'VALUES (?, ?, ?, ?, ?)',
            (session_id, pattern_type, columns_involved, description, strength)
        )
        conn.commit()
        return cursor.lastrowid

    def get_patterns(self, session_id: int) -> List[PatternRecord]:
        """Retrieve all patterns for a session."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM patterns WHERE session_id = ? ORDER BY pattern_id',
            (session_id,)
        ).fetchall()
        return [self._row_to_pattern(r) for r in rows]

    @staticmethod
    def _row_to_pattern(row: sqlite3.Row) -> PatternRecord:
        return PatternRecord(
            pattern_id=row['pattern_id'],
            session_id=row['session_id'],
            pattern_type=row['pattern_type'],
            columns_involved=row['columns_involved'],
            description=row['description'],
            strength=row['strength'],
        )

    # ------------------------------------------------------------------
    # Table 6: rule_definitions (FR-041 – FR-049)
    # ------------------------------------------------------------------

    def sync_rule_definitions(self, rules: List[Dict[str, Any]]):
        """Synchronize the rule_definitions table from a parsed rules list.

        This replaces all existing rule_definitions with the contents of the
        provided list (typically loaded from engineering_rules.json).

        FR-041: Maintain a human-editable rule file.
        FR-048: Validate rule file syntax on load.
        """
        conn = self.get_connection()
        conn.execute('DELETE FROM rule_definitions')
        for rule in rules:
            conn.execute(
                'INSERT INTO rule_definitions '
                '(rule_id, rule_name, condition_json, conclusion_text, '
                'recommendation_text, scope_pattern, is_enabled) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    rule['rule_id'],
                    rule['rule_name'],
                    json.dumps(rule.get('condition', {})),
                    rule['conclusion_text'],
                    rule.get('recommendation_text'),
                    rule.get('scope_pattern'),
                    rule.get('is_enabled', True),
                )
            )
        conn.commit()
        logger.info('Synced %d rule definitions to database.', len(rules))

    def get_rule_definitions(self, enabled_only: bool = False) -> List[RuleDefinitionRecord]:
        """Retrieve rule definitions from the database.

        Args:
            enabled_only: If True, only returns rules where is_enabled = 1.
        """
        conn = self.get_connection()
        query = 'SELECT * FROM rule_definitions'
        if enabled_only:
            query += ' WHERE is_enabled = 1'
        rows = conn.execute(query).fetchall()
        return [self._row_to_rule_def(r) for r in rows]

    def update_rule_enabled(self, rule_id: str, is_enabled: bool):
        """Enable or disable a rule without deleting it (FR-045)."""
        conn = self.get_connection()
        conn.execute(
            'UPDATE rule_definitions SET is_enabled = ? WHERE rule_id = ?',
            (is_enabled, rule_id)
        )
        conn.commit()

    @staticmethod
    def _row_to_rule_def(row: sqlite3.Row) -> RuleDefinitionRecord:
        return RuleDefinitionRecord(
            rule_id=row['rule_id'],
            rule_name=row['rule_name'],
            condition_json=row['condition_json'],
            conclusion_text=row['conclusion_text'],
            recommendation_text=row['recommendation_text'],
            scope_pattern=row['scope_pattern'],
            is_enabled=bool(row['is_enabled']),
        )

    # ------------------------------------------------------------------
    # Table 7: rule_matches (FR-043, FR-046)
    # ------------------------------------------------------------------

    def insert_rule_match(self, session_id: int, rule_id: str,
                          matched_on: Optional[str] = None) -> int:
        """Insert a record of a rule that fired for a session.

        FR-046: Log every rule that fired, including which condition triggered it.

        Returns:
            The auto-generated match_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO rule_matches (session_id, rule_id, matched_on) '
            'VALUES (?, ?, ?)',
            (session_id, rule_id, matched_on)
        )
        conn.commit()
        return cursor.lastrowid

    def get_rule_matches(self, session_id: int) -> List[RuleMatchRecord]:
        """Retrieve all rule matches for a session."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM rule_matches WHERE session_id = ? '
            'ORDER BY match_id',
            (session_id,)
        ).fetchall()
        return [self._row_to_rule_match(r) for r in rows]

    @staticmethod
    def _row_to_rule_match(row: sqlite3.Row) -> RuleMatchRecord:
        return RuleMatchRecord(
            match_id=row['match_id'],
            session_id=row['session_id'],
            rule_id=row['rule_id'],
            matched_on=row['matched_on'],
            matched_at=row['matched_at'],
        )

    # ------------------------------------------------------------------
    # Table 8: insights (FR-051 – FR-058)
    # ------------------------------------------------------------------

    def insert_insight(self, session_id: int, source_type: str,
                       source_id: Optional[int], text: str) -> int:
        """Insert a generated natural-language insight.

        FR-055: Template-based NLG only — never a generative LLM.

        Returns:
            The auto-generated insight_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO insights (session_id, source_type, source_id, text) '
            'VALUES (?, ?, ?, ?)',
            (session_id, source_type, source_id, text)
        )
        conn.commit()
        return cursor.lastrowid

    def get_insights(self, session_id: int) -> List[InsightRecord]:
        """Retrieve all insights for a session."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM insights WHERE session_id = ? ORDER BY insight_id',
            (session_id,)
        ).fetchall()
        return [self._row_to_insight(r) for r in rows]

    def delete_insights(self, session_id: int):
        """Delete all insights for a session (used before regeneration, FR-057)."""
        conn = self.get_connection()
        conn.execute(
            'DELETE FROM insights WHERE session_id = ?', (session_id,)
        )
        conn.commit()

    @staticmethod
    def _row_to_insight(row: sqlite3.Row) -> InsightRecord:
        return InsightRecord(
            insight_id=row['insight_id'],
            session_id=row['session_id'],
            source_type=row['source_type'],
            source_id=row['source_id'],
            text=row['text'],
        )

    # ------------------------------------------------------------------
    # Table 9: recommendations (FR-059 – FR-065)
    # ------------------------------------------------------------------

    def insert_recommendation(self, session_id: int, text: str,
                              severity: str,
                              source_rule_id: Optional[str] = None,
                              engineer_note: Optional[str] = None) -> int:
        """Insert a recommendation linked to a finding.

        FR-063: Recommendations reference the rule or detection method.

        Returns:
            The auto-generated recommendation_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO recommendations '
            '(session_id, text, severity, source_rule_id, engineer_note) '
            'VALUES (?, ?, ?, ?, ?)',
            (session_id, text, severity, source_rule_id, engineer_note)
        )
        conn.commit()
        return cursor.lastrowid

    def get_recommendations(self, session_id: int) -> List[RecommendationRecord]:
        """Retrieve recommendations for a session, ranked by severity (FR-061).

        Order: Critical first, then Warning, then Info.
        """
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM recommendations WHERE session_id = ? '
            "ORDER BY CASE severity "
            "WHEN 'Critical' THEN 1 WHEN 'Warning' THEN 2 "
            "WHEN 'Info' THEN 3 END, recommendation_id",
            (session_id,)
        ).fetchall()
        return [self._row_to_recommendation(r) for r in rows]

    def update_recommendation_note(self, recommendation_id: int,
                                   engineer_note: str):
        """Update the engineer's free-text annotation on a recommendation (FR-062)."""
        conn = self.get_connection()
        conn.execute(
            'UPDATE recommendations SET engineer_note = ? '
            'WHERE recommendation_id = ?',
            (engineer_note, recommendation_id)
        )
        conn.commit()

    def delete_recommendations(self, session_id: int):
        """Delete all recommendations for a session (used before regeneration)."""
        conn = self.get_connection()
        conn.execute(
            'DELETE FROM recommendations WHERE session_id = ?', (session_id,)
        )
        conn.commit()

    @staticmethod
    def _row_to_recommendation(row: sqlite3.Row) -> RecommendationRecord:
        return RecommendationRecord(
            recommendation_id=row['recommendation_id'],
            session_id=row['session_id'],
            text=row['text'],
            severity=row['severity'],
            source_rule_id=row['source_rule_id'],
            engineer_note=row['engineer_note'],
        )

    # ------------------------------------------------------------------
    # Table 10: reports (FR-071 – FR-080)
    # ------------------------------------------------------------------

    def insert_report(self, session_id: int, file_path: str,
                      report_format: str = 'PDF',
                      included_charts: bool = True) -> int:
        """Insert a report metadata record.

        Returns:
            The auto-generated report_id.
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'INSERT INTO reports '
            '(session_id, file_path, format, included_charts) '
            'VALUES (?, ?, ?, ?)',
            (session_id, file_path, report_format, included_charts)
        )
        conn.commit()
        return cursor.lastrowid

    def get_reports(self, session_id: int) -> List[ReportRecord]:
        """Retrieve all reports for a session."""
        conn = self.get_connection()
        rows = conn.execute(
            'SELECT * FROM reports WHERE session_id = ? '
            'ORDER BY generated_on DESC',
            (session_id,)
        ).fetchall()
        return [self._row_to_report(r) for r in rows]

    @staticmethod
    def _row_to_report(row: sqlite3.Row) -> ReportRecord:
        return ReportRecord(
            report_id=row['report_id'],
            session_id=row['session_id'],
            file_path=row['file_path'],
            format=row['format'],
            generated_on=row['generated_on'],
            included_charts=bool(row['included_charts']),
        )

    # ------------------------------------------------------------------
    # Table 11: app_settings (FR-091 – FR-097)
    # ------------------------------------------------------------------

    def get_setting(self, key: str) -> Optional[str]:
        """Retrieve a single setting value by key."""
        conn = self.get_connection()
        row = conn.execute(
            'SELECT setting_value FROM app_settings WHERE setting_key = ?',
            (key,)
        ).fetchone()
        return row['setting_value'] if row else None

    def set_setting(self, key: str, value: str):
        """Insert or update a single setting (FR-095)."""
        conn = self.get_connection()
        conn.execute(
            'INSERT INTO app_settings (setting_key, setting_value, updated_on) '
            'VALUES (?, ?, ?) '
            'ON CONFLICT(setting_key) DO UPDATE SET '
            'setting_value = excluded.setting_value, '
            'updated_on = excluded.updated_on',
            (key, value, datetime.now().isoformat())
        )
        conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        """Retrieve all settings as a flat key-value dict."""
        conn = self.get_connection()
        rows = conn.execute('SELECT * FROM app_settings').fetchall()
        return {row['setting_key']: row['setting_value'] for row in rows}

    def sync_settings_from_json(self, settings_path: str):
        """Populate app_settings from a settings.json file.

        Flattens the nested JSON structure into dot-separated keys:
        e.g. {"detection": {"zscore_threshold": 3.0}}
        becomes key="detection.zscore_threshold", value="3.0".

        FR-095: Store all configuration in settings.json.
        """
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        flat = self._flatten_dict(settings)
        for key, value in flat.items():
            self.set_setting(key, str(value))
        logger.info('Synced %d settings from %s', len(flat), settings_path)

    @staticmethod
    def _flatten_dict(d: Dict, parent_key: str = '',
                      sep: str = '.') -> Dict[str, Any]:
        """Flatten a nested dict into dot-separated keys."""
        items: List = []
        for k, v in d.items():
            new_key = f'{parent_key}{sep}{k}' if parent_key else k
            if isinstance(v, dict):
                items.extend(
                    DatabaseManager._flatten_dict(v, new_key, sep).items()
                )
            else:
                items.append((new_key, v))
        return dict(items)

    # ------------------------------------------------------------------
    # Utility: load settings.json as a nested dict
    # ------------------------------------------------------------------

    @staticmethod
    def load_settings_json(settings_path: str) -> Dict[str, Any]:
        """Load and return settings.json as a nested Python dict.

        This is a convenience method for GUI and core modules that need
        the full settings structure (not flattened keys).

        Raises:
            FileNotFoundError: If the settings file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def save_settings_json(settings_path: str, settings: Dict[str, Any]):
        """Write the settings dict back to settings.json (FR-095).

        Preserves the nested structure used by the rest of the application.
        """
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write('\n')
