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
