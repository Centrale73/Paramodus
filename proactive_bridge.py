"""
Enhanced ApiBridge with Proactive Task Support
Extends existing bridge.py with proactive monitoring capabilities
"""

import os
import threading
import json
import base64
import uuid
import logging
from datetime import datetime, timedelta
from agents.workspace_agent import get_agent, ingest_files, clear_knowledge_base
from database import save_msg, get_history, clear_session, get_all_sessions

# Proactive imports
from proactive_database import (
    create_proactive_task,
    get_session_tasks_sync,
    get_session_alerts_sync,
    update_task_status,
    get_task_stats,
    get_session_stats,
    get_unacknowledged_count,
    get_task_from_db
)
from scheduler import start_scheduler, stop_scheduler, add_proactive_task, remove_proactive_task
import asyncio

logger = logging.getLogger(__name__)


class ProactiveApiBridge:
    """Enhanced ApiBridge with proactive monitoring capabilities."""
    
    def __init__(self):
        # Original properties
        self.keys = {
            "openai": os.environ.get("OPENAI_API_KEY"),
            "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
            "gemini": os.environ.get("GEMINI_API_KEY"),
            "groq": os.environ.get("GROQ_API_KEY"),
            "grok": os.environ.get("XAI_API_KEY"),
            "openrouter": os.environ.get("OPENROUTER_API_KEY"),
            "perplexity": os.environ.get("PERPLEXITY_API_KEY")
        }
        self.current_provider = os.environ.get("DEFAULT_PROVIDER", "openai")
        self.current_model = os.environ.get("DEFAULT_MODEL", None)
        self.window = None
        self.multi_agent_mode = False
        self.uploaded_filenames = []
        self.current_session_id = str(uuid.uuid4())
        
        # Proactive properties
        self.scheduler_started = False
        self.proactive_notifications = []  # Queue for UI notifications
        
    def set_window(self, window):
        """Set the pywebview window and start scheduler."""
        self.window = window
        
        # Start proactive scheduler with notification callback and current provider
        if not self.scheduler_started:
            start_scheduler(
                notification_callback=self._handle_proactive_notification,
                provider=self.current_provider,
                api_key=self.keys.get(self.current_provider)
            )
            self.scheduler_started = True
            logger.info(f"Proactive scheduler started with provider: {self.current_provider}")
    
    def _handle_proactive_notification(
        self,
        session_id: str,
        task_type: str,
        alert_type: str,
        message: str,
        task_id: str
    ):
        """
        Callback function for proactive notifications.
        Sends notifications to the UI via JavaScript.
        """
        if not self.window:
            return
        
        notification = {
            'session_id': session_id,
            'task_type': task_type,
            'alert_type': alert_type,
            'message': message,
            'task_id': task_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store notification
        self.proactive_notifications.append(notification)
        
        # Send to UI via JavaScript
        try:
            js_code = f"receiveProactiveNotification({json.dumps(notification)})"
            self.window.evaluate_js(js_code)
            logger.info(f"Sent proactive notification for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to send notification to UI: {e}")
    
    # ========================================================================
    # ORIGINAL METHODS (preserved from original ApiBridge)
    # ========================================================================
    
    def new_session(self):
        """Start a new conversation session."""
        self.current_session_id = str(uuid.uuid4())
        return {"status": "success", "session_id": self.current_session_id}

    def list_sessions(self):
        """Retrieve list of all sessions."""
        return get_all_sessions()

    def switch_session(self, session_id):
        """Switch to a specific session."""
        self.current_session_id = session_id
        return {"status": "success", "session_id": session_id}

    def get_current_session_id(self):
        """Return the current session ID."""
        return self.current_session_id

    def set_api_key(self, key, provider="openai"):
        self.keys[provider] = key
        env_var = f"{provider.upper()}_API_KEY"
        if provider == "grok": env_var = "XAI_API_KEY"
        os.environ[env_var] = key
        return f"{provider.title()} key saved"

    def set_provider(self, provider):
        if provider in self.keys:
            self.current_provider = provider
            return f"Provider switched to {provider}"
        return "Invalid provider"

    def set_model(self, model_id):
        self.current_model = model_id if model_id else None
        return f"Model set to {model_id if model_id else 'default'}"

    def toggle_multi_agent(self, enabled):
        self.multi_agent_mode = enabled
        return f"Multi-Agent mode: {'Enabled' if enabled else 'Disabled'}"

    def load_history(self):
        return get_history(self.current_session_id)

    def clear_rag_context(self):
        clear_knowledge_base()
        self.uploaded_filenames = []
        return "RAG context cleared"

    def upload_files(self, files_json):
        try:
            files_data = json.loads(files_json) if isinstance(files_json, str) else files_json
            processed_files = []
            for f in files_data:
                name = f["name"]
                content_b64 = f["content"]
                if "," in content_b64:
                    content_b64 = content_b64.split(",")[1]
                data = base64.b64decode(content_b64)
                processed_files.append({"name": name, "data": data})
                self.uploaded_filenames.append(name)
            
            success = ingest_files(processed_files)
            if success:
                return {"status": "success", "files": list(set(self.uploaded_filenames))}
            return {"status": "error", "message": "Failed to ingest files"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def start_chat_stream(self, user_text, target_id=None):
        api_key = self.keys.get(self.current_provider)
        if not api_key:
            self.window.evaluate_js(f"receiveError('Please set your {self.current_provider.title()} API Key first.')")
            return
         
        if not target_id:
            save_msg("user", user_text, self.current_session_id)

        thread = threading.Thread(target=self._run_logic, args=(user_text, target_id))
        thread.daemon = True
        thread.start()

    def _run_logic(self, user_text, target_id):
        if self.multi_agent_mode:
            self._run_multi_agent(user_text, target_id)
        else:
            self._run_single_agent(user_text, target_id)

    def _run_single_agent(self, user_text, target_id):
        try:
            provider = self.current_provider
            api_key = self.keys.get(provider)
            model_id = self.current_model
            
            agent = get_agent(
                provider=provider, 
                api_key=api_key, 
                model_id=model_id, 
                user_id="default_user",
                session_id=self.current_session_id
            )
            full_response = ""
            run_response = agent.run(user_text, stream=True)
            
            if target_id:
                self.window.evaluate_js(f"clearBubble('{target_id}')")

            for chunk in run_response:
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content:
                    full_response += content
                    self.window.evaluate_js(f"receiveChunk({json.dumps(content)}, '{target_id or ''}')")

            save_msg("bot", full_response, self.current_session_id)
            
            tone = self._detect_tone(full_response)
            self.window.evaluate_js(f"streamComplete({json.dumps(tone)})")
        except Exception as e:
            self.window.evaluate_js(f"receiveError({json.dumps(str(e))})")
    
    def _detect_tone(self, text):
        """Simple keyword-based tone detection for GenUI."""
        text_lower = text.lower()
        scores = {
            'excited': 0,
            'playful': 0,
            'serious': 0,
            'calm': 0
        }
        
        excited_words = ['!', 'amazing', 'awesome', 'fantastic', 'great', 'excellent']
        for word in excited_words:
            scores['excited'] += text_lower.count(word)
        
        playful_words = ['😊', '😄', '🎉', 'haha', 'fun', 'enjoy', 'play']
        for word in playful_words:
            scores['playful'] += text_lower.count(word)
        
        serious_words = ['important', 'critical', 'warning', 'caution', 'error']
        for word in serious_words:
            scores['serious'] += text_lower.count(word)
        
        calm_words = ['here', 'let me', 'simply', 'just', 'easy', 'step']
        for word in calm_words:
            scores['calm'] += text_lower.count(word)
        
        if max(scores.values()) == 0:
            return 'calm'
        
        return max(scores, key=scores.get)

    def _run_multi_agent(self, user_text, target_id):
        self._run_single_agent(user_text, target_id)
    
    # ========================================================================
    # PROACTIVE TASK MANAGEMENT METHODS
    # ========================================================================
    
    def create_proactive_task(self, task_type, task_config, interval_seconds=3600):
        """
        Create a new proactive monitoring task.
        
        Args:
            task_type: Type of task (monitor_url, monitor_file, daily_briefing, etc.)
            task_config: Configuration dict (url, path, topics, etc.)
            interval_seconds: Check interval in seconds
        
        Returns:
            dict with status and task_id
        """
        try:
            # Create task in database
            task_id = asyncio.run(create_proactive_task(
                session_id=self.current_session_id,
                task_type=task_type,
                task_config=task_config,
                interval_seconds=interval_seconds
            ))
            
            # Add to scheduler
            success = add_proactive_task(
                task_id=task_id,
                task_type=task_type,
                task_config=task_config,
                notification_callback=self._handle_proactive_notification,
                provider=self.current_provider,
                api_key=self.keys.get(self.current_provider)
            )
            
            if success:
                logger.info(f"Created proactive task {task_id} of type {task_type}")
                return {
                    "status": "success",
                    "task_id": task_id,
                    "message": f"Proactive task created: {task_type}"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to add task to scheduler"
                }
                
        except Exception as e:
            logger.error(f"Error creating proactive task: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_proactive_tasks(self):
        """Get all proactive tasks for current session."""
        try:
            tasks = get_session_tasks_sync(self.current_session_id)
            return {
                "status": "success",
                "tasks": tasks,
                "count": len(tasks)
            }
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return {
                "status": "error",
                "message": str(e),
                "tasks": []
            }
    
    def pause_proactive_task(self, task_id):
        """Pause a proactive task."""
        try:
            # Update database
            asyncio.run(update_task_status(task_id, 'paused'))
            
            # Remove from scheduler
            remove_proactive_task(task_id)
            
            logger.info(f"Paused proactive task {task_id}")
            return {
                "status": "success",
                "message": "Task paused"
            }
        except Exception as e:
            logger.error(f"Error pausing task: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def resume_proactive_task(self, task_id):
        """Resume a paused task."""
        try:
            # Get task from database
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task = loop.run_until_complete(get_task_from_db(task_id))
            loop.close()
            
            if not task:
                return {"status": "error", "message": "Task not found"}
            
            # Update status
            asyncio.run(update_task_status(task_id, 'active'))
            
            # Re-add to scheduler
            task_config = json.loads(task['task_config']) if isinstance(task['task_config'], str) else task['task_config']
            add_proactive_task(
                task_id=task_id,
                task_type=task['task_type'],
                task_config=task_config,
                notification_callback=self._handle_proactive_notification,
                provider=self.current_provider,
                api_key=self.keys.get(self.current_provider)
            )
            
            logger.info(f"Resumed proactive task {task_id}")
            return {
                "status": "success",
                "message": "Task resumed"
            }
        except Exception as e:
            logger.error(f"Error resuming task: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_proactive_alerts(self, limit=50):
        """Get alerts for current session."""
        try:
            alerts = get_session_alerts_sync(
                self.current_session_id,
                limit=limit
            )
            return {
                "status": "success",
                "alerts": alerts,
                "count": len(alerts)
            }
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return {
                "status": "error",
                "message": str(e),
                "alerts": []
            }
    
    def get_unacknowledged_alerts(self):
        """Get count of unacknowledged alerts."""
        try:
            count = asyncio.run(get_unacknowledged_count(self.current_session_id))
            return {
                "status": "success",
                "count": count
            }
        except Exception as e:
            logger.error(f"Error getting unacknowledged count: {e}")
            return {
                "status": "error",
                "count": 0
            }
    
    def get_task_statistics(self, task_id):
        """Get execution statistics for a task."""
        try:
            stats = asyncio.run(get_task_stats(task_id))
            return {
                "status": "success",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Error getting task stats: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_session_statistics(self):
        """Get overall statistics for current session."""
        try:
            stats = asyncio.run(get_session_stats(self.current_session_id))
            return {
                "status": "success",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def __del__(self):
        """Cleanup: stop scheduler when bridge is destroyed."""
        if self.scheduler_started:
            stop_scheduler()
