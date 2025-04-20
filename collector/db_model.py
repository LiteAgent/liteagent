import re
from typing import Any

from sqlalchemy import Column, Integer, Sequence, String, inspect, Float, Index
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


async def create_interaction_event_class(task: str, engine: AsyncEngine) -> Any:
    """
    Dynamically creates a InteractionEvent ORM class based on the provided task name.
    Adds an additional 'input_value' column to store input data.

    Args:
        task (str): The task name used to generate a unique table name.
        engine (AsyncEngine): The SQLAlchemy asynchronous engine.

    Returns:
        Any: The dynamically created InteractionEvent class.
    """
    # Sanitize the task name to create a valid table name
    task = re.sub(r"[^\w\s-]", "_", task.strip())
    task = re.sub(r"\s+", "_", task)
    task = task.lower()

    if not task:
        task = "default_task_name"

    # Check if the table already exists
    async with engine.connect() as conn:
        existing_tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

    # Ensure a unique table name by appending a counter if needed
    base_task_name = task
    counter = 1
    while task in existing_tables:
        task = f"{base_task_name}_{counter}"
        counter += 1

    # Dynamically create a class with a unique name based on the task
    class_name = f"InteractionEvent_{task}"

    InteractionEvent = type(
        class_name,
        (Base,),
        {
            "__tablename__": task,
            "__table_args__": (Index("ix_time_since_last_action", "time_since_last_action"), {"extend_existing": True}),
            "id": Column(Integer, Sequence("clicked_element_id_seq"), primary_key=True),
            "event_type": Column(String(50), nullable=False),
            "xpath": Column(String(250), nullable=True),
            "class_name": Column(String(250), nullable=True),
            "element_id": Column(String(250), nullable=True),
            "input_value": Column(String(250), nullable=True),
            "url": Column(String(500), nullable=True),
            "additional_info": Column(String(500), nullable=True),
            "time_since_last_action": Column(Float, nullable=True),
        },
    )

    # Ensure the table is created
    async with engine.begin() as conn:
        await conn.run_sync(InteractionEvent.metadata.create_all)

    return InteractionEvent
