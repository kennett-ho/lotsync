"""
Sprint 03 -- database/engine.py's pure-Python surface: engine
selection and the qmark->format SQL translation. No database (of
either kind) is touched here; the translator is exactly the kind of
string-walking logic that deserves direct unit coverage, since a
translation bug would corrupt every PostgreSQL query at once.
"""

import os
import unittest
from unittest import mock

from lotsync.database.engine import get_engine, translate_qmark_sql


class GetEngineTest(unittest.TestCase):
    def test_defaults_to_sqlite_when_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_ENGINE"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(get_engine(), "sqlite")

    def test_postgres_when_set(self):
        with mock.patch.dict(os.environ, {"DATABASE_ENGINE": "postgres"}):
            self.assertEqual(get_engine(), "postgres")

    def test_case_and_whitespace_are_tolerated(self):
        with mock.patch.dict(os.environ, {"DATABASE_ENGINE": "  Postgres "}):
            self.assertEqual(get_engine(), "postgres")

    def test_unknown_engine_is_refused_loudly(self):
        with mock.patch.dict(os.environ, {"DATABASE_ENGINE": "mysql"}):
            with self.assertRaises(ValueError):
                get_engine()


class TranslateQmarkSqlTest(unittest.TestCase):
    def test_plain_placeholders(self):
        self.assertEqual(
            translate_qmark_sql("SELECT * FROM t WHERE a = ? AND b = ?"),
            "SELECT * FROM t WHERE a = %s AND b = %s",
        )

    def test_no_placeholders_passes_through(self):
        self.assertEqual(translate_qmark_sql("SELECT 1"), "SELECT 1")

    def test_question_mark_inside_string_literal_is_preserved(self):
        self.assertEqual(
            translate_qmark_sql("SELECT * FROM t WHERE a = '?' AND b = ?"),
            "SELECT * FROM t WHERE a = '?' AND b = %s",
        )

    def test_escaped_quote_inside_literal(self):
        # 'it''s ?' is ONE literal containing "it's ?" -- the ? inside
        # must survive; the one outside must translate.
        self.assertEqual(
            translate_qmark_sql("SELECT 'it''s ?' , ?"),
            "SELECT 'it''s ?' , %s",
        )

    def test_percent_is_escaped_for_psycopg(self):
        # Escaped even inside the quoted literal -- psycopg's parser
        # does not understand SQL quoting (see the LIKE test below).
        self.assertEqual(
            translate_qmark_sql("SELECT strftime('%Y', x) FROM t WHERE a = ?"),
            "SELECT strftime('%%Y', x) FROM t WHERE a = %s",
        )

    def test_percent_inside_literal_is_also_escaped(self):
        # psycopg parses % client-side in the whole query string, so a
        # LIKE '%abc%' literal must become '%%abc%%' regardless of
        # quoting context.
        self.assertEqual(
            translate_qmark_sql("SELECT * FROM t WHERE a LIKE '%abc%'"),
            "SELECT * FROM t WHERE a LIKE '%%abc%%'",
        )

    def test_double_quoted_identifier_with_question_mark(self):
        self.assertEqual(
            translate_qmark_sql('SELECT "weird?col" FROM t WHERE a = ?'),
            'SELECT "weird?col" FROM t WHERE a = %s',
        )

    def test_real_repository_statement_translates_cleanly(self):
        sql = (
            "INSERT INTO event_freshness (vin, event_type, source, last_observed_at, last_sync_run_id) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(vin, event_type) DO UPDATE SET "
            "source = excluded.source, last_observed_at = excluded.last_observed_at, "
            "last_sync_run_id = excluded.last_sync_run_id"
        )
        translated = translate_qmark_sql(sql)
        self.assertEqual(translated.count("%s"), 5)
        self.assertNotIn("?", translated)


if __name__ == "__main__":
    unittest.main()
