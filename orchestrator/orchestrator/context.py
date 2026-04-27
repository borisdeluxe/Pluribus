"""Context building for agent handoffs - passes prior artifacts in prompt."""

from pathlib import Path
from typing import Optional

# Which artifacts each agent needs from prior stages
AGENT_CONTEXT_MAP = {
    "concept_clarifier": [],  # First agent, no prior context
    "architect_planner": ["tk-draft.md"],
    "test_designer": ["tk-draft.md", "plan.md"],
    "implementer": ["tk-draft.md", "plan.md", "test-plan.md"],
    "security_reviewer": ["tk-draft.md", "plan.md", "implementation.md"],
    "refactorer": ["tk-draft.md", "plan.md", "implementation.md", "security-report.md"],
    "qa_validator": ["tk-draft.md", "plan.md", "implementation.md", "security-report.md", "refactor-report.md"],
    "docs_updater": ["tk-draft.md", "plan.md", "implementation.md", "qa-report.md"],
    "deploy_runner": ["tk-draft.md", "plan.md", "implementation.md", "qa-report.md", "docs-report.md"],
}


def build_agent_context(
    pipeline_dir: Path,
    feature_id: str,
    agent: str,
    input_content: str = "",
) -> str:
    """Build context string with all prior artifacts for an agent.

    Args:
        pipeline_dir: Base pipeline directory (e.g., /opt/agency/.pipeline)
        feature_id: Feature ID (e.g., "MOBILE-004")
        agent: Current agent name
        input_content: Original input/task description

    Returns:
        Full context string with input + all prior artifacts
    """
    feature_dir = pipeline_dir / feature_id
    context_parts = []

    # Always include original input
    if input_content:
        context_parts.append(f"# Original Task\n\n{input_content}")
    elif (feature_dir / "input.md").exists():
        context_parts.append(f"# Original Task\n\n{(feature_dir / 'input.md').read_text()}")

    # Add prior artifacts based on agent
    required_artifacts = AGENT_CONTEXT_MAP.get(agent, [])
    for artifact_name in required_artifacts:
        artifact_path = feature_dir / artifact_name
        if artifact_path.exists():
            content = artifact_path.read_text()
            # Use filename as section header
            section_name = artifact_name.replace("-", " ").replace(".md", "").title()
            context_parts.append(f"# {section_name}\n\n{content}")

    return "\n\n---\n\n".join(context_parts)


def get_last_status(pipeline_dir: Path, feature_id: str) -> Optional[str]:
    """Get the last STATUS line from the most recent artifact."""
    feature_dir = pipeline_dir / feature_id

    # Check artifacts in reverse order
    artifact_order = [
        "deploy-log.md",
        "docs-report.md",
        "qa-report.md",
        "refactor-report.md",
        "security-report.md",
        "implementation.md",
        "test-plan.md",
        "plan.md",
        "tk-draft.md",
    ]

    for artifact_name in artifact_order:
        artifact_path = feature_dir / artifact_name
        if artifact_path.exists():
            content = artifact_path.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("STATUS:"):
                    return line[7:].strip()

    return None
