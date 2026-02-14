"""
Test Script for Proactive Agent System
Run this to verify your installation is working correctly
"""

import asyncio
import sys
from datetime import datetime, timedelta

# Test imports
print("Testing imports...")
try:
    from proactive_database import (
        init_proactive_database,
        create_proactive_task,
        get_active_tasks,
        get_task_from_db
    )
    print("✓ Database module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import database module: {e}")
    sys.exit(1)

try:
    from proactive_agents import create_sentry_agent, create_chief_agent, MonitorResult, ActionDecision
    print("✓ Agents module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import agents module: {e}")
    sys.exit(1)

try:
    from scheduler import start_scheduler, stop_scheduler
    print("✓ Scheduler module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import scheduler module: {e}")
    sys.exit(1)


async def test_database():
    """Test database initialization and CRUD operations."""
    print("\n" + "="*60)
    print("TEST 1: Database Operations")
    print("="*60)
    
    # Initialize database
    print("\n1. Initializing database...")
    try:
        await init_proactive_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    
    # Create a test task
    print("\n2. Creating test task...")
    try:
        task_id = await create_proactive_task(
            session_id="test-session",
            task_type="monitor_url",
            task_config={
                "url": "https://httpbin.org/status/200",
                "expected_status": 200,
                "timeout": 30,
                "interval": 60
            },
            interval_seconds=60
        )
        print(f"✓ Task created with ID: {task_id}")
    except Exception as e:
        print(f"✗ Task creation failed: {e}")
        return False
    
    # Retrieve the task
    print("\n3. Retrieving task...")
    try:
        task = await get_task_from_db(task_id)
        if task:
            print(f"✓ Task retrieved successfully")
            print(f"  - Type: {task['task_type']}")
            print(f"  - Status: {task['status']}")
            print(f"  - Created: {task['created_at']}")
        else:
            print("✗ Task not found")
            return False
    except Exception as e:
        print(f"✗ Task retrieval failed: {e}")
        return False
    
    # List active tasks
    print("\n4. Listing active tasks...")
    try:
        tasks = await get_active_tasks()
        print(f"✓ Found {len(tasks)} active task(s)")
    except Exception as e:
        print(f"✗ Listing tasks failed: {e}")
        return False
        
    return True


def test_sentry_agent():
    """Test Sentry Agent with a simple health check."""
    print("\n" + "="*60)
    print("TEST 2: Sentry Agent")
    print("="*60)
    
    # Determine provider from environment
    import os
    provider = os.environ.get("TEST_PROVIDER", "openai")
    print(f"\n1. Testing Sentry Agent with {provider} provider...")
    
    try:
        # Create agent with specified provider
        sentry_agent = create_sentry_agent(provider=provider)
        
        result = sentry_agent.run(
            message="""Execute a test health check.
Task: Monitor URL https://httpbin.org/status/200
Expected: Status code 200
Report the result in structured format.""",
            session_id="test-sentry"
        )
        
        monitor_result: MonitorResult = result.content
        print(f"✓ Sentry Agent responded")
        print(f"  - Status: {monitor_result.status}")
        print(f"  - Escalation needed: {monitor_result.requires_escalation}")
        print(f"  - Summary: {monitor_result.summary}")
        
        if hasattr(monitor_result, 'status'):
            print("✓ Response has correct structure (MonitorResult)")
            return True
        else:
            print("✗ Response structure is incorrect")
            return False
            
    except Exception as e:
        print(f"✗ Sentry Agent test failed: {e}")
        return False


def test_chief_agent():
    """Test Chief Agent with a simulated escalation."""
    print("\n" + "="*60)
    print("TEST 3: Chief Agent")
    print("="*60)
    
    # Determine provider from environment
    import os
    provider = os.environ.get("TEST_PROVIDER", "openai")
    print(f"\n1. Testing Chief Agent with {provider} provider...")
    
    try:
        # Create agent with specified provider
        chief_agent = create_chief_agent(provider=provider)
        
        result = chief_agent.run(
            message="""Sentry Agent has detected an issue requiring your attention:

**Status:** degraded
**Summary:** API endpoint response time increased significantly
**Data:** {
  "url": "https://api.example.com/health",
  "avg_response_time": 2.5,
  "threshold": 1.0,
  "timestamp": "2024-01-15T10:30:00Z"
}

Please analyze this situation and decide on the appropriate action.""",
            session_id="test-chief"
        )
        
        action: ActionDecision = result.content
        print(f"✓ Chief Agent responded")
        print(f"  - Action: {action.action_type}")
        print(f"  - Message: {action.message[:100]}...")
        print(f"  - Next check: {action.suggested_next_check}s")
        
        if hasattr(action, 'action_type'):
            print("✓ Response has correct structure (ActionDecision)")
            return True
        else:
            print("✗ Response structure is incorrect")
            return False
            
    except Exception as e:
        print(f"✗ Chief Agent test failed: {e}")
        return False


def test_scheduler_initialization():
    """Test scheduler initialization."""
    print("\n" + "="*60)
    print("TEST 4: Scheduler")
    print("="*60)
    
    print("\n1. Testing scheduler initialization...")
    try:
        # Don't actually start it to avoid long-running process
        from apscheduler.schedulers.background import BackgroundScheduler
        test_scheduler = BackgroundScheduler()
        print("✓ Scheduler can be instantiated")
        
        # Test job addition
        def dummy_job():
            pass
            
        test_scheduler.add_job(
            dummy_job,
            'interval',
            seconds=60,
            id='test-job'
        )
        print("✓ Job can be added to scheduler")
        
        # Clean up
        test_scheduler.remove_job('test-job')
        print("✓ Job can be removed from scheduler")
        
        return True
    except Exception as e:
        print(f"✗ Scheduler test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests and report results."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "PROACTIVE SYSTEM TEST SUITE" + " "*15 + "║")
    print("╚" + "="*58 + "╝")
    
    results = {}
    
    # Test 1: Database
    results['Database'] = await test_database()
    
    # Test 2: Sentry Agent
    results['Sentry Agent'] = test_sentry_agent()
    
    # Test 3: Chief Agent
    results['Chief Agent'] = test_chief_agent()
    
    # Test 4: Scheduler
    results['Scheduler'] = test_scheduler_initialization()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False
            
    print("="*60)
    
    if all_passed:
        print("\n🎉 All tests passed! Your proactive system is ready to use.")
        print("\nNext steps:")
        print("1. Run your main application with the ProactiveApiBridge")
        print("2. Create your first monitoring task via the UI")
        print("3. Watch the logs for Sentry -> Chief escalations")
        print("\n💡 Multi-Provider Support:")
        print("The system will use whatever provider you select in the UI!")
        print("Supported: OpenAI, Anthropic, Google, Groq, xAI, OpenRouter, Perplexity")
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
        print("\nCommon issues:")
        print("- Missing dependencies: pip install -r requirements_proactive.txt")
        print("- Missing API key: Set OPENAI_API_KEY in .env")
        print("- Database permissions: Check ~/.myapp/ directory")
        
    return all_passed


if __name__ == "__main__":
    # Check for API key
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.environ.get('OPENAI_API_KEY'):
        print("⚠️ WARNING: OPENAI_API_KEY not found in environment")
        print("Agent tests will fail without an API key.\n")
        print("Add to .env file:")
        print("OPENAI_API_KEY=sk-your-key-here\n")
    
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
