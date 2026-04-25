"""Agency CLI - submit tasks and check status."""
import click
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


PIPELINE_DIR = Path(os.environ.get('AGENCY_PIPELINE_DIR', '/opt/agency/.pipeline'))
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://agency:agency@localhost:5432/agency_db')


def get_db():
    """Get database connection."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def generate_feature_id() -> str:
    """Generate a unique feature ID."""
    timestamp = datetime.now().strftime('%H%M%S')
    return f"CLI-{timestamp}"


@click.group()
def cli():
    """Mutirada Agency - Autonomous Development Pipeline."""
    pass


@cli.command()
@click.argument('title')
@click.option('--body', '-b', default='', help='Task description')
@click.option('--id', 'feature_id', default=None, help='Custom feature ID (default: auto-generated)')
@click.option('--priority', '-p', default=0, help='Priority (higher = sooner)')
def submit(title: str, body: str, feature_id: str, priority: int):
    """Submit a new feature task to the pipeline.

    Example:
        agency submit "Add rate limiting" --body "Max 100 req/min"
    """
    if not feature_id:
        feature_id = generate_feature_id()

    # Create pipeline directory
    feature_dir = PIPELINE_DIR / feature_id
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Write input.md
    input_content = f"""# {title}

## Description

{body if body else 'No description provided.'}

## Metadata

- Feature ID: {feature_id}
- Source: CLI
- Created: {datetime.now().isoformat()}
"""
    (feature_dir / 'input.md').write_text(input_content)

    # Insert into database
    data = json.dumps({'title': title, 'body': body})

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO agency_tasks (feature_id, source, priority, data)
            VALUES (%s, %s, %s, %s)
            """,
            (feature_id, 'cli', priority, data)
        )
        conn.commit()

    click.echo(f"Task created: {feature_id}")
    click.echo(f"Input file: {feature_dir / 'input.md'}")


@cli.command()
@click.argument('target', required=False)
@click.option('--pr', 'pr_number', default=None, type=int, help='GitHub PR number')
def review(target: str, pr_number: int):
    """Submit a review-only task (skips to security_reviewer).

    Example:
        agency review src/api/billing.py
        agency review --pr 42
    """
    if not target and not pr_number:
        raise click.UsageError('Provide a path or --pr number')

    feature_id = f"REVIEW-{datetime.now().strftime('%H%M%S')}"

    if pr_number:
        review_target = f"PR #{pr_number}"
        data = json.dumps({'pr_number': pr_number})
    else:
        review_target = target
        data = json.dumps({'path': target})

    # Create pipeline directory
    feature_dir = PIPELINE_DIR / feature_id
    feature_dir.mkdir(parents=True, exist_ok=True)

    # Write input.md
    input_content = f"""# Review Request

## Target

{review_target}

## Metadata

- Feature ID: {feature_id}
- Source: review
- Created: {datetime.now().isoformat()}
"""
    (feature_dir / 'input.md').write_text(input_content)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO agency_tasks (feature_id, source, data)
            VALUES (%s, %s, %s)
            """,
            (feature_id, 'review', data)
        )
        conn.commit()

    click.echo(f"Review task created: {feature_id}")
    click.echo(f"Target: {review_target}")


@cli.command()
def status():
    """Show current pipeline status and budget."""
    with get_db() as conn:
        # Active tasks
        tasks = conn.execute(
            """
            SELECT feature_id, status, current_agent, cost_eur, created_at
            FROM agency_tasks
            WHERE status IN ('pending', 'in_progress')
            ORDER BY created_at DESC
            LIMIT 20
            """
        ).fetchall()

        # Daily budget
        daily = conn.execute(
            """
            SELECT COALESCE(SUM(cost_eur), 0) as total
            FROM agency_tasks
            WHERE created_at >= CURRENT_DATE
            """
        ).fetchone()

    click.echo("\n=== Active Tasks ===\n")

    if not tasks:
        click.echo("No active tasks.")
    else:
        for task in tasks:
            agent = task['current_agent'] or 'waiting'
            cost = float(task['cost_eur'] or 0)
            click.echo(f"  {task['feature_id']:12} | {task['status']:12} | {agent:20} | €{cost:.2f}")

    click.echo("\n=== Budget ===\n")
    daily_total = float(daily['total']) if daily else 0
    click.echo(f"  Today: €{daily_total:.2f} / €20.00")
    click.echo(f"  Remaining: €{20.00 - daily_total:.2f}")
    click.echo()


@cli.command()
@click.argument('feature_id')
def cancel(feature_id: str):
    """Cancel a pending or in-progress task."""
    with get_db() as conn:
        result = conn.execute(
            """
            UPDATE agency_tasks
            SET status = 'cancelled', updated_at = NOW()
            WHERE feature_id = %s AND status IN ('pending', 'in_progress')
            RETURNING feature_id
            """,
            (feature_id,)
        ).fetchone()
        conn.commit()

    if result:
        click.echo(f"Cancelled: {feature_id}")
    else:
        click.echo(f"Task not found or already completed: {feature_id}")


if __name__ == '__main__':
    cli()
