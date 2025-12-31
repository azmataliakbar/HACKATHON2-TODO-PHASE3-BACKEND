from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from src.core.database import get_async_session
from src.models import Task, TaskCreate, TaskUpdate, TaskRead
from src.services.crud import (
    get_tasks, 
    create_task, 
    update_task, 
    delete_task,
    complete_task
)

router = APIRouter()


@router.get("/tasks/{user_id}", response_model=List[TaskRead])
async def list_tasks(
    user_id: str,
    status: Optional[str] = "all",  # all, pending, completed
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all tasks for a user
    
    Parameters:
    - user_id: User's unique identifier
    - status: Filter by status (all/pending/completed)
    
    Returns:
    - List of tasks
    """
    tasks = await get_tasks(session, user_id, status)
    return tasks


@router.post("/tasks/{user_id}", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def add_task(
    user_id: str,
    task_data: TaskCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new task
    
    Parameters:
    - user_id: User's unique identifier
    - task_data: Task details (title, description)
    
    Returns:
    - Created task
    """
    task = await create_task(session, user_id, task_data)
    return task


@router.put("/tasks/{user_id}/{task_id}", response_model=TaskRead)
async def modify_task(
    user_id: str,
    task_id: int,
    task_data: TaskUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update an existing task
    
    Parameters:
    - user_id: User's unique identifier
    - task_id: Task ID to update
    - task_data: Updated task details
    
    Returns:
    - Updated task
    """
    task = await update_task(session, user_id, task_id, task_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or does not belong to user"
        )
    return task


@router.delete("/tasks/{user_id}/{task_id}")
async def remove_task(
    user_id: str,
    task_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete a task
    
    Parameters:
    - user_id: User's unique identifier
    - task_id: Task ID to delete
    
    Returns:
    - Deletion confirmation
    """
    success = await delete_task(session, user_id, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or does not belong to user"
        )
    return {
        "status": "deleted",
        "task_id": task_id,
        "message": f"Task {task_id} has been deleted successfully"
    }


@router.patch("/tasks/{user_id}/{task_id}/complete", response_model=TaskRead)
async def mark_complete(
    user_id: str,
    task_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Mark a task as complete
    
    Parameters:
    - user_id: User's unique identifier
    - task_id: Task ID to mark as complete
    
    Returns:
    - Updated task with completed status
    """
    task = await complete_task(session, user_id, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or does not belong to user"
        )
    return task