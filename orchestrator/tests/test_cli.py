"""Tests for agency CLI."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

from orchestrator.cli import cli, submit, review, status


class TestSubmitCommand:
    """agency submit should create tasks."""

    def test_submit_creates_task(self, runner, mock_db, tmp_path):
        """Should insert task into database."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(submit, ['Add rate limiting'])

        assert result.exit_code == 0
        assert 'Task created' in result.output

    def test_submit_with_body(self, runner, mock_db, tmp_path):
        """Should accept --body for description."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(submit, [
                    'Add rate limiting',
                    '--body', 'Max 100 requests per minute per API key'
                ])

        assert result.exit_code == 0

    def test_submit_with_feature_id(self, runner, mock_db, tmp_path):
        """Should accept --id for custom feature ID."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(submit, [
                    'Add rate limiting',
                    '--id', 'FAL-99'
                ])

        assert result.exit_code == 0
        assert 'FAL-99' in result.output

    def test_submit_generates_feature_id(self, runner, mock_db, tmp_path):
        """Should generate feature ID if not provided."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(submit, ['Add rate limiting'])

        assert result.exit_code == 0
        # Should contain generated ID like CLI-1234
        assert 'CLI-' in result.output or 'Task created' in result.output

    def test_submit_writes_input_md(self, runner, mock_db, tmp_path):
        """Should write input.md to pipeline directory."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(submit, [
                    'Add rate limiting',
                    '--body', 'Description here',
                    '--id', 'TEST-1'
                ])

        input_file = tmp_path / 'TEST-1' / 'input.md'
        assert input_file.exists()
        content = input_file.read_text()
        assert 'Add rate limiting' in content
        assert 'Description here' in content


class TestReviewCommand:
    """agency review should create review-only tasks."""

    def test_review_path(self, runner, mock_db, tmp_path):
        """Should create review task for file path."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(review, ['src/api/billing.py'])

        assert result.exit_code == 0
        assert 'Review task created' in result.output

    def test_review_pr(self, runner, mock_db, tmp_path):
        """Should create review task for PR number."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(review, ['--pr', '42'])

        assert result.exit_code == 0
        assert 'PR #42' in result.output or 'Review task created' in result.output

    def test_review_sets_source(self, runner, mock_db, tmp_path):
        """Should set source='review' for review tasks."""
        with patch('orchestrator.cli.get_db', return_value=mock_db):
            with patch('orchestrator.cli.PIPELINE_DIR', tmp_path):
                result = runner.invoke(review, ['src/api/'])

        assert result.exit_code == 0
        # Verify source is 'review' in DB call
        assert len(mock_db._queries) > 0
        query, params = mock_db._queries[-1]
        assert 'review' in params  # source='review'


class TestStatusCommand:
    """agency status should show pipeline state."""

    def test_status_shows_active_tasks(self, runner):
        """Should list active tasks."""
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {'feature_id': 'FAL-47', 'status': 'in_progress', 'current_agent': 'implementer', 'cost_eur': 1.5, 'created_at': '2026-01-01'},
        ]
        mock_cursor.fetchone.return_value = {'total': 5.0}
        mock_conn.execute.return_value = mock_cursor

        with patch('orchestrator.cli.get_db', return_value=mock_conn):
            result = runner.invoke(status)

        assert result.exit_code == 0
        assert 'FAL-47' in result.output

    def test_status_shows_budget(self, runner):
        """Should show budget consumption."""
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = {'total': 12.50}
        mock_conn.execute.return_value = mock_cursor

        with patch('orchestrator.cli.get_db', return_value=mock_conn):
            result = runner.invoke(status)

        assert result.exit_code == 0
        assert 'Budget' in result.output


class TestCliHelp:
    """CLI should have helpful documentation."""

    def test_main_help(self, runner):
        """Should show main help."""
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert 'submit' in result.output
        assert 'review' in result.output
        assert 'status' in result.output

    def test_submit_help(self, runner):
        """Should show submit help."""
        result = runner.invoke(submit, ['--help'])

        assert result.exit_code == 0
        assert '--body' in result.output
        assert '--id' in result.output


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()
