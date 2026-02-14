"""
Proactive Task Scheduler for Agentic Workspace
Replaces OpenClaw's Gateway Cron with APScheduler + SQLite
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import json
import uuid
from typing import Optional, Dict, Any
import logging

from proactive_agents import create_sentry_agent, create_chief_agent, MonitorResult, ActionDecision
from proactive_database import (
    get_task_from_db,
    update_task_execution,
    create_alert,
    update_next_execution,
    get_active_tasks
)

logger = logging.getLogger(__name__)

# Configure scheduler with SQLite persistence
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///scheduler.db')
}

scheduler = BackgroundScheduler(jobstores=jobstores)


async def execute_proactive_task(task_id: str, notification_callback=None, provider="openai", api_key=None):
    """
    Core proactive execution loop:
    1. Load task config from database
    2. Execute Sentry Agent check
    3. If escalation needed, invoke Chief Agent
    4. Update task state and schedule next run
    5. Notify user via callback if needed
    
    Args:
        task_id: UUID of the task to execute
        notification_callback: Function to call for user notifications
        provider: LLM provider to use (openai, anthropic, gemini, etc.)
        api_key: API key for the provider
    """
    try:
        # Fetch task from database
        task = await get_task_from_db(task_id)
        
        if not task or task['status'] != 'active':
            logger.info(f"Task {task_id} is not active, skipping")
            return
        
        logger.info(f"Executing proactive task: {task['task_type']} for session {task['session_id']} using {provider}")
        
        # Parse task config
        task_config = json.loads(task['task_config']) if isinstance(task['task_config'], str) else task['task_config']
        
        # Create agents with specified provider
        sentry_agent = create_sentry_agent(provider=provider, api_key=api_key)
        
        # Execute Sentry check
        sentry_message = build_sentry_prompt(task['task_type'], task_config)
        
        result = sentry_agent.run(
            message=sentry_message,
            session_id=task['session_id']
        )
        
        # Parse structured output
        monitor_result: MonitorResult = result.content
        
        # Update task execution metadata
        await update_task_execution(
            task_id=task_id,
            last_execution=datetime.utcnow(),
            execution_count=task['execution_count'] + 1
        )
        
        # Escalation logic
        if monitor_result.requires_escalation:
            logger.warning(f"Sentry escalating task {task_id}: {monitor_result.summary}")
            
            # Create Chief Agent with specified provider
            chief_agent = create_chief_agent(provider=provider, api_key=api_key)
            
            # Invoke Chief Agent for decision
            chief_message = f"""Sentry Agent has detected an issue requiring your attention:

**Status:** {monitor_result.status}
**Summary:** {monitor_result.summary}
**Data:** {json.dumps(monitor_result.data, indent=2)}

Please analyze this situation and decide on the appropriate action."""
            
            decision_result = chief_agent.run(
                message=chief_message,
                session_id=task['session_id']
            )
            
            action: ActionDecision = decision_result.content
            
            # Record alert
            await create_alert(
                task_id=task_id,
                session_id=task['session_id'],
                alert_type='critical' if monitor_result.status == 'critical' else 'warning',
                message=action.message,
                data=monitor_result.data
            )
            
            # Notify user via callback
            if notification_callback:
                notification_callback(
                    session_id=task['session_id'],
                    task_type=task['task_type'],
                    alert_type='critical' if monitor_result.status == 'critical' else 'warning',
                    message=action.message,
                    task_id=task_id
                )
            
            # Adjust schedule if suggested
            if action.suggested_next_check != task_config.get('interval', 3600):
                logger.info(f"Adjusting task {task_id} interval to {action.suggested_next_check}s")
                task_config['interval'] = action.suggested_next_check
                # Update scheduler job
                scheduler.reschedule_job(
                    job_id=task_id,
                    trigger=IntervalTrigger(seconds=action.suggested_next_check)
                )
        else:
            # Silent success - no user notification
            logger.info(f"Task {task_id} completed successfully: {monitor_result.summary}")
        
        # Schedule next execution
        next_run = datetime.utcnow() + timedelta(seconds=task_config.get('interval', 3600))
        await update_next_execution(task_id, next_run)
        
    except Exception as e:
        logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
        # Record failure (could implement exponential backoff here)


def build_sentry_prompt(task_type: str, task_config: dict) -> str:
    """Build appropriate prompt for Sentry Agent based on task type."""
    
    if task_type == "monitor_url":
        return f"""Execute a health check on the following endpoint:
URL: {task_config.get('url')}
Expected Status: {task_config.get('expected_status', 200)}
Timeout: {task_config.get('timeout', 30)} seconds

Check if the endpoint is responding correctly. Set requires_escalation=True only if:
- Status code is not as expected
- Response time exceeds threshold
- Endpoint is unreachable

Return structured MonitorResult."""
    
    elif task_type == "monitor_file":
        return f"""Check the status of the following file:
Path: {task_config.get('path')}
Watch for: {task_config.get('watch_for', 'changes')}

Monitor for file changes, size increases, or specific patterns. Set requires_escalation=True only if:
- File size changed significantly
- New error patterns detected
- File disappeared

Return structured MonitorResult."""
    
    elif task_type == "daily_briefing":
        return f"""Generate a daily briefing on the following topics:
Topics: {', '.join(task_config.get('topics', []))}

Compile relevant updates and insights. Set requires_escalation=True only if:
- Critical news detected
- Significant developments in monitored areas

Return structured MonitorResult."""
    
    elif task_type == "custom_check":
        return f"""Execute custom monitoring task:
{task_config.get('description', '')}

Commands to run: {task_config.get('commands', [])}
Thresholds: {task_config.get('thresholds', {})}

Set requires_escalation=True only if thresholds are exceeded or anomalies detected.

Return structured MonitorResult."""
    
    else:
        return f"""Execute monitoring task of type: {task_type}
Configuration: {json.dumps(task_config, indent=2)}

Analyze the situation and determine if escalation is needed.
Return structured MonitorResult."""


def start_scheduler(notification_callback=None, provider="openai", api_key=None):
    """
    Start the APScheduler and load all active tasks.
    
    Args:
        notification_callback: Function to call when user notification is needed
        provider: LLM provider to use for agents (openai, anthropic, gemini, etc.)
        api_key: API key for the provider
    """
    logger.info(f"Starting proactive task scheduler with provider: {provider}...")
    
    # This will be called asynchronously, but we need to handle it in sync context
    import asyncio
    
    # Get event loop or create one
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Load all active tasks and register them
    active_tasks = loop.run_until_complete(get_active_tasks())
    
    logger.info(f"Found {len(active_tasks)} active proactive tasks")
    
    for task in active_tasks:
        try:
            task_config = json.loads(task['task_config']) if isinstance(task['task_config'], str) else task['task_config']
            interval = task_config.get('interval', 3600)
            
            # Determine trigger type
            if task['task_type'] == 'daily_briefing':
                # Use cron trigger for daily briefings
                trigger = CronTrigger(
                    hour=task_config.get('hour', 9),
                    minute=task_config.get('minute', 0)
                )
            else:
                # Use interval trigger for monitoring tasks
                trigger = IntervalTrigger(seconds=interval)
            
            # Create wrapper that passes notification callback and provider
            def task_wrapper(tid=task['task_id'], callback=notification_callback, prov=provider, key=api_key):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(execute_proactive_task(tid, callback, prov, key))
                loop.close()
            
            scheduler.add_job(
                task_wrapper,
                trigger=trigger,
                id=str(task['task_id']),
                next_run_time=datetime.fromisoformat(task['next_execution']) if task.get('next_execution') else None,
                replace_existing=True  # Resume existing jobs after restart
            )
            
            logger.info(f"Registered task {task['task_id']} ({task['task_type']}) with {interval}s interval")
            
        except Exception as e:
            logger.error(f"Failed to register task {task['task_id']}: {e}")
    
    scheduler.start()
    logger.info("Proactive task scheduler started successfully")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    logger.info("Stopping proactive task scheduler...")
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


def add_proactive_task(
    task_id: str,
    task_type: str,
    task_config: dict,
    notification_callback=None,
    provider="openai",
    api_key=None
) -> bool:
    """
    Add a new task to the scheduler dynamically.
    
    Args:
        task_id: UUID of the task
        task_type: Type of monitoring task
        task_config: Configuration dictionary
        notification_callback: Function to call for notifications
        provider: LLM provider to use
        api_key: API key for the provider
    
    Returns:
        bool: True if successfully added
    """
    try:
        interval = task_config.get('interval', 3600)
        
        # Determine trigger type
        if task_type == 'daily_briefing':
            trigger = CronTrigger(
                hour=task_config.get('hour', 9),
                minute=task_config.get('minute', 0)
            )
        else:
            trigger = IntervalTrigger(seconds=interval)
        
        # Create wrapper
        import asyncio
        def task_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(execute_proactive_task(task_id, notification_callback, provider, api_key))
            loop.close()
        
        scheduler.add_job(
            task_wrapper,
            trigger=trigger,
            id=str(task_id),
            replace_existing=True
        )
        
        logger.info(f"Added new proactive task {task_id} ({task_type})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add task {task_id}: {e}")
        return False


def remove_proactive_task(task_id: str) -> bool:
    """
    Remove a task from the scheduler.
    
    Args:
        task_id: UUID of the task
    
    Returns:
        bool: True if successfully removed
    """
    try:
        scheduler.remove_job(str(task_id))
        logger.info(f"Removed proactive task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to remove task {task_id}: {e}")
        return False
