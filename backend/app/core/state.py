import asyncio
import logging

logger = logging.getLogger(__name__)

app_state = {
    "vector_db": None,
    "llm": None,
    "embed_model": None,
    "metadata": None,
    "initialized": False,
    "init_lock": asyncio.Lock(),
    "init_attempts": 0,
}

def get_app_state():
    """Get app state dictionary"""
    return app_state

def is_initialized():
    """Check if app is initialized"""
    return app_state.get("initialized", False)

def set_initialized(status: bool):
    """Set initialization status"""
    app_state["initialized"] = status
    logger.info(f"📊 App initialization status set to: {status}")

def mark_as_initialized():
    """Mark app as initialized (convenience function)"""
    set_initialized(True)
    logger.info("✅ App marked as fully initialized")

def get_service(service_name: str):
    """Get specific service from app state"""
    return app_state.get(service_name)

def set_service(service_name: str, service_instance):
    """Set specific service in app state"""
    app_state[service_name] = service_instance
    logger.info(f"✅ Service '{service_name}' registered in app state")

def reset_app_state():
    """Reset app state (for testing/debugging)"""
    global app_state
    app_state = {
        "vector_db": None,
        "llm": None,
        "embed_model": None,
        "metadata": None,
        "initialized": False,
        "init_lock": asyncio.Lock(),
        "init_attempts": 0,
    }
    logger.info("🔄 App state reset")

def get_init_attempts():
    """Get number of initialization attempts"""
    return app_state.get("init_attempts", 0)

def increment_init_attempts():
    """Increment initialization attempts counter"""
    app_state["init_attempts"] = app_state.get("init_attempts", 0) + 1
    logger.info(f"🔢 Initialization attempts: {app_state['init_attempts']}")

def get_init_lock():
    """Get initialization lock"""
    return app_state.get("init_lock")

# Debug function to check state
def debug_app_state():
    """Debug current app state"""
    logger.info("🔍 Current app state:")
    for key, value in app_state.items():
        if key == "init_lock":
            logger.info(f"  - {key}: {type(value).__name__}")
        elif value is None:
            logger.info(f"  - {key}: None")
        else:
            logger.info(f"  - {key}: {type(value).__name__} ({'initialized' if hasattr(value, '__dict__') else 'object'})")