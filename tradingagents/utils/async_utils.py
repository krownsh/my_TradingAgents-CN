
import asyncio
import threading
from typing import TypeVar, Coroutine, Any

T = TypeVar("T")

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine synchronously.
    Handles cases where there is already a running event loop (e.g. Jupyter, Uvicorn).
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If loop is running, we cannot just use run_until_complete on it.
        # We must use a separate thread or nest_asyncio.
        # For simplicity and safety, use a separate thread with a new loop.
        
        result = None
        exception = None
        
        def run_in_thread():
            nonlocal result, exception
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result = new_loop.run_until_complete(coro)
            except Exception as e:
                exception = e
            finally:
                new_loop.close()
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()
        
        if exception:
            raise exception
        return result
    else:
        # No loop running, or we can get/create one.
        try:
            if not loop:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        except RuntimeError as e:
            # Fallback for "Lock is held" or similar
            if "already running" in str(e):
                 # Should be caught by is_running() check above, but double check
                 pass
            raise e
