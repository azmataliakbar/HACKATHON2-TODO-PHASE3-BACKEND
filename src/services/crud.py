from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_
from typing import List, Optional
from datetime import datetime
from src.models import Task, TaskCreate, TaskUpdate, Conversation, Message, MessageCreate


async def create_task(session: AsyncSession, user_id: str, task_data: TaskCreate) -> Task:
    """Create a new task for the specified user."""
    task = Task(
        title=task_data.title,
        description=task_data.description,
        completed=task_data.completed,
        user_id=user_id
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    return task


async def get_tasks(session: AsyncSession, user_id: str, status: Optional[str] = "all") -> List[Task]:
    """Get all tasks for the specified user, optionally filtered by completion status."""
    query = select(Task).where(Task.user_id == user_id)

    if status == "pending":
        query = query.where(Task.completed == False)
    elif status == "completed":
        query = query.where(Task.completed == True)

    result = await session.execute(query)
    tasks = result.scalars().all()

    return tasks


async def get_task(session: AsyncSession, user_id: str, task_id: int) -> Optional[Task]:
    """Get a specific task for the specified user."""
    query = select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    return task


async def update_task(session: AsyncSession, user_id: str, task_id: int, task_data: TaskUpdate) -> Optional[Task]:
    """Update a specific task for the specified user."""
    query = select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        return None

    # Update fields that were provided
    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.completed is not None:
        task.completed = task_data.completed
        # Update completed_at timestamp if task is being marked as completed
        if task_data.completed and not task.completed:
            task.completed_at = datetime.utcnow()
        elif not task_data.completed:
            task.completed_at = None

    # Update the updated_at timestamp
    task.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(task)

    return task


async def delete_task(session: AsyncSession, user_id: str, task_id: int) -> bool:
    """Delete a specific task for the specified user."""
    query = select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        return False

    await session.delete(task)
    await session.commit()

    return True


async def complete_task(session: AsyncSession, user_id: str, task_id: int, completed: bool) -> Optional[Task]:
    """Mark a specific task as completed or pending for the specified user."""
    query = select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        return None

    task.completed = completed
    if completed:
        task.completed_at = datetime.utcnow()
    else:
        task.completed_at = None

    task.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(task)

    return task


async def create_conversation(session: AsyncSession, user_id: str) -> Conversation:
    """Create a new conversation for the specified user."""
    conversation = Conversation(user_id=user_id)

    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    return conversation


async def get_conversation(session: AsyncSession, conversation_id: int) -> Optional[Conversation]:
    """Get a specific conversation by ID."""
    query = select(Conversation).where(Conversation.id == conversation_id)
    result = await session.execute(query)
    conversation = result.scalar_one_or_none()

    return conversation


async def create_message(session: AsyncSession, message_data: MessageCreate) -> Message:
    """Create a new message in a conversation."""
    message = Message(
        user_id=message_data.user_id,
        conversation_id=message_data.conversation_id,
        role=message_data.role,
        content=message_data.content
    )

    session.add(message)
    await session.commit()
    await session.refresh(message)

    return message


async def get_messages_for_conversation(session: AsyncSession, conversation_id: int) -> List[Message]:
    """Get all messages for a specific conversation."""
    query = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    result = await session.execute(query)
    messages = result.scalars().all()

    return messages