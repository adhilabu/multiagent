"""SqliteSaver configuration for persistence and time-travel debugging."""

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from langgraph.checkpoint.sqlite import SqliteSaver


def get_db_path() -> str:
    """Get the database path from environment or use default."""
    return os.getenv("CHECKPOINT_DB_PATH", "research_checkpoints.db")


def get_checkpointer(db_path: str | None = None) -> SqliteSaver:
    """
    Configure SqliteSaver for local persistence.
    
    Enables:
    - Checkpoint every node execution
    - Time-travel debugging
    - Session resume after interruption
    
    Args:
        db_path: Optional custom database path
        
    Returns:
        Configured SqliteSaver instance
    """
    path = db_path or get_db_path()
    # Create sqlite3 connection directly and pass to SqliteSaver
    # from_conn_string() returns a context manager, not a SqliteSaver instance
    conn = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(conn)


@contextmanager
def checkpointer_context(db_path: str | None = None):
    """
    Context manager for SqliteSaver to ensure proper cleanup.
    
    Usage:
        with checkpointer_context() as checkpointer:
            app = graph.compile(checkpointer=checkpointer)
            result = app.invoke(state)
    """
    checkpointer = get_checkpointer(db_path)
    try:
        yield checkpointer
    finally:
        # SqliteSaver handles connection cleanup internally
        pass


def list_checkpoints(thread_id: str, db_path: str | None = None) -> list[dict]:
    """
    List all checkpoints for a given thread (for time-travel debugging).
    
    Args:
        thread_id: The thread/session ID to query
        db_path: Optional custom database path
        
    Returns:
        List of checkpoint metadata dictionaries
    """
    checkpointer = get_checkpointer(db_path)
    config = {"configurable": {"thread_id": thread_id}}
    
    checkpoints = []
    for checkpoint in checkpointer.list(config):
        checkpoints.append({
            "checkpoint_id": checkpoint.config.get("configurable", {}).get("checkpoint_id"),
            "thread_id": thread_id,
            "metadata": checkpoint.metadata,
        })
    
    return checkpoints


def get_checkpoint_state(
    thread_id: str, 
    checkpoint_id: str | None = None,
    db_path: str | None = None
) -> dict | None:
    """
    Retrieve state at a specific checkpoint (for time-travel).
    
    Args:
        thread_id: The thread/session ID
        checkpoint_id: Specific checkpoint to retrieve (None = latest)
        db_path: Optional custom database path
        
    Returns:
        State dictionary at that checkpoint, or None if not found
    """
    checkpointer = get_checkpointer(db_path)
    
    config = {"configurable": {"thread_id": thread_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
    
    checkpoint = checkpointer.get_tuple(config)
    if checkpoint:
        # CheckpointTuple has channel_values attribute containing the state dict
        return checkpoint.checkpoint.get('channel_values')
    return None


def list_all_sessions(db_path: str | None = None) -> list[dict]:
    """
    List all unique research sessions from the database.
    
    Args:
        db_path: Optional custom database path
        
    Returns:
        List of session info dictionaries with thread_id and metadata
    """
    path = db_path or get_db_path()
    
    if not Path(path).exists():
        return []
    
    conn = sqlite3.connect(path, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Query unique thread_ids from checkpoints table
        # The SqliteSaver uses a 'checkpoints' table with thread_id column
        cursor.execute("""
            SELECT DISTINCT thread_id 
            FROM checkpoints 
            ORDER BY thread_id
        """)
        
        sessions = []
        for (thread_id,) in cursor.fetchall():
            # Get the latest checkpoint state for each session
            state = get_checkpoint_state(thread_id, db_path=db_path)
            
            if state:
                sessions.append({
                    "thread_id": thread_id,
                    "user_query": state.get("user_query", "Unknown"),
                    "status": _determine_status(state),
                    "revision_count": state.get("revision_count", 0),
                    "has_final_response": bool(state.get("final_response")),
                })
            else:
                sessions.append({
                    "thread_id": thread_id,
                    "user_query": "Unknown",
                    "status": "unknown",
                    "revision_count": 0,
                    "has_final_response": False,
                })
        
        return sessions
    except sqlite3.OperationalError:
        # Table might not exist yet
        return []
    finally:
        conn.close()


def _determine_status(state: dict) -> str:
    """Determine the current status based on state."""
    if state.get("final_response"):
        return "completed"
    if state.get("latest_critique") and not state.get("human_approved"):
        return "awaiting_approval"
    if state.get("current_plan"):
        return "researching"
    return "pending"
