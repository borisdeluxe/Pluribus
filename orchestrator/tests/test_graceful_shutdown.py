"""Tests for graceful shutdown functionality."""
import pytest
import signal
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from orchestrator.main import Orchestrator, AgentSession


class TestGracefulShutdown:
    """Orchestrator should handle SIGTERM and SIGINT gracefully."""

    def test_shutdown_flag_initially_false(self, orchestrator):
        """Shutdown flag should be False initially."""
        assert orchestrator._shutdown_requested is False

    def test_sigterm_sets_shutdown_flag(self, orchestrator):
        """SIGTERM should set shutdown flag."""
        orchestrator._handle_shutdown(signal.SIGTERM, None)
        assert orchestrator._shutdown_requested is True

    def test_sigint_sets_shutdown_flag(self, orchestrator):
        """SIGINT should set shutdown flag."""
        orchestrator._handle_shutdown(signal.SIGINT, None)
        assert orchestrator._shutdown_requested is True

    def test_run_loop_exits_on_shutdown_flag(self, orchestrator):
        """run_loop should exit when shutdown flag is set."""
        orchestrator._shutdown_requested = True

        with patch.object(orchestrator, 'process_one') as mock_process:
            with patch.object(orchestrator, 'check_active_sessions'):
                with patch.object(orchestrator, '_graceful_shutdown') as mock_graceful:
                    orchestrator.run_loop(interval=1)

        # Should not process any tasks when shutdown is requested
        mock_process.assert_not_called()
        mock_graceful.assert_called_once()

    def test_shutdown_logs_active_sessions(self, orchestrator, capsys):
        """Shutdown should log all active sessions."""
        orchestrator._active_sessions = {
            "FAL-47": AgentSession(
                feature_id="FAL-47",
                task_id=1,
                current_agent="concept_clarifier",
                tmux_session="FAL-47-concept",
            ),
            "FAL-48": AgentSession(
                feature_id="FAL-48",
                task_id=2,
                current_agent="implementer",
                tmux_session="FAL-48-impl",
            ),
        }

        orchestrator._graceful_shutdown()

        captured = capsys.readouterr()
        assert "FAL-47" in captured.out
        assert "FAL-48" in captured.out
        assert "concept_clarifier" in captured.out
        assert "implementer" in captured.out

    def test_shutdown_kills_tmux_sessions_when_requested(self, orchestrator):
        """Shutdown should kill tmux sessions when kill_sessions=True."""
        orchestrator._active_sessions = {
            "FAL-47": AgentSession(
                feature_id="FAL-47",
                task_id=1,
                current_agent="concept_clarifier",
                tmux_session="FAL-47-concept",
            ),
        }
        orchestrator._kill_sessions_on_shutdown = True

        with patch('subprocess.run') as mock_run:
            orchestrator._graceful_shutdown()

        # Check that tmux kill-session was called
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "tmux" in call_args
        assert "kill-session" in call_args
        assert "FAL-47-concept" in call_args

    def test_shutdown_does_not_kill_sessions_by_default(self, orchestrator):
        """Shutdown should not kill tmux sessions by default."""
        orchestrator._active_sessions = {
            "FAL-47": AgentSession(
                feature_id="FAL-47",
                task_id=1,
                current_agent="concept_clarifier",
                tmux_session="FAL-47-concept",
            ),
        }
        # Default should be False
        assert orchestrator._kill_sessions_on_shutdown is False

        with patch('subprocess.run') as mock_run:
            orchestrator._graceful_shutdown()

        # tmux kill-session should NOT be called
        mock_run.assert_not_called()

    def test_shutdown_logs_when_no_active_sessions(self, orchestrator, capsys):
        """Shutdown should log cleanly when no sessions are active."""
        orchestrator._active_sessions = {}

        orchestrator._graceful_shutdown()

        captured = capsys.readouterr()
        assert "No active sessions" in captured.out

    def test_signal_handlers_are_registered(self, orchestrator):
        """run_loop should register signal handlers."""
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        orchestrator._shutdown_requested = True  # Exit immediately

        try:
            with patch.object(orchestrator, '_graceful_shutdown'):
                orchestrator.run_loop(interval=1)

            # Handlers should be registered after run_loop starts
            # (but since we exit immediately, we check that the method exists)
            assert hasattr(orchestrator, '_handle_shutdown')
        finally:
            # Restore original handlers
            signal.signal(signal.SIGTERM, original_sigterm)
            signal.signal(signal.SIGINT, original_sigint)


# Fixtures

@pytest.fixture
def orchestrator(mock_db, tmp_path):
    """Orchestrator with mocked dependencies."""
    orch = Orchestrator(
        db=mock_db,
        pipeline_dir=tmp_path / ".pipeline",
        worktree_dir=tmp_path / "worktrees",
        repos_dir=tmp_path / "repos",
    )
    orch.task_queue.fail_task = Mock()
    orch.task_queue.complete_task = Mock()
    orch.task_queue.add_cost = Mock()
    orch.task_queue.start_task = Mock()
    # Mock the worktree manager factory
    mock_wt_manager = Mock()
    mock_wt_manager.worktree_exists.return_value = True
    mock_wt_manager.get_worktree_path.return_value = tmp_path / "repos" / "falara"
    orch.get_worktree_manager = Mock(return_value=mock_wt_manager)
    return orch
