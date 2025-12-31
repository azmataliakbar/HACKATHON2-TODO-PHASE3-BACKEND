"""
MCP Server for Todo AI Chatbot
Implements Model Context Protocol tools that wrap Phase 2 CRUD functions
"""
import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from src.services.crud import (
    create_task, get_tasks, update_task, delete_task, complete_task,
    create_conversation, create_message, get_messages_for_conversation
)
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_session
from src.models import TaskCreate, TaskUpdate, MessageCreate


class MCPTool(BaseModel):
    """Base class for MCP tools"""
    name: str
    description: str
    parameters: Dict[str, Any]


class AddTaskInput(BaseModel):
    user_id: str
    title: str
    description: str = ""


class ListTasksInput(BaseModel):
    user_id: str
    status: str = "all"  # all, pending, completed


class CompleteTaskInput(BaseModel):
    user_id: str
    task_id: int


class DeleteTaskInput(BaseModel):
    user_id: str
    task_id: int


class UpdateTaskInput(BaseModel):
    user_id: str
    task_id: int
    title: str = None
    description: str = None


class MCPServer:
    """Model Context Protocol Server that exposes tools for AI agents"""

    def __init__(self):
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available MCP tools"""
        self.tools["add_task"] = {
            "function": self.add_task,
            "description": "Create a new task for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The ID of the user"},
                    "title": {"type": "string", "description": "The title of the task"},
                    "description": {"type": "string", "description": "Optional description of the task"}
                },
                "required": ["user_id", "title"]
            }
        }

        self.tools["list_tasks"] = {
            "function": self.list_tasks,
            "description": "List all tasks for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The ID of the user"},
                    "status": {"type": "string", "description": "Filter by status: all, pending, completed", "enum": ["all", "pending", "completed"]}
                },
                "required": ["user_id"]
            }
        }

        self.tools["complete_task"] = {
            "function": self.complete_task,
            "description": "Mark a task as completed or pending",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The ID of the user"},
                    "task_id": {"type": "integer", "description": "The ID of the task to update"},
                    "completed": {"type": "boolean", "description": "Whether the task is completed or not"}
                },
                "required": ["user_id", "task_id", "completed"]
            }
        }

        self.tools["delete_task"] = {
            "function": self.delete_task,
            "description": "Delete a task",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The ID of the user"},
                    "task_id": {"type": "integer", "description": "The ID of the task to delete"}
                },
                "required": ["user_id", "task_id"]
            }
        }

        self.tools["update_task"] = {
            "function": self.update_task,
            "description": "Update a task's details",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The ID of the user"},
                    "task_id": {"type": "integer", "description": "The ID of the task to update"},
                    "title": {"type": "string", "description": "New title for the task (optional)"},
                    "description": {"type": "string", "description": "New description for the task (optional)"}
                },
                "required": ["user_id", "task_id"]
            }
        }

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool with given parameters"""
        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}

        try:
            # Get the tool function
            tool_info = self.tools[tool_name]
            func = tool_info["function"]

            # Execute the tool with parameters
            result = await func(**parameters)
            return {"result": result}
        except Exception as e:
            return {"error": f"Error executing tool {tool_name}: {str(e)}"}

    async def add_task(self, user_id: str, title: str, description: str = "") -> Dict[str, Any]:
        """Add a new task for the user"""
        from src.core.database import async_engine
        async with AsyncSession(async_engine) as session:
            task_data = TaskCreate(title=title, description=description, completed=False)
            task = await create_task(session, user_id, task_data)
            return {
                "task_id": task.id,
                "status": "created",
                "title": task.title
            }

    async def list_tasks(self, user_id: str, status: str = "all") -> List[Dict[str, Any]]:
        """List tasks for the user"""
        from src.core.database import async_engine
        async with AsyncSession(async_engine) as session:
            tasks = await get_tasks(session, user_id, status)
            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "completed": task.completed,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                }
                for task in tasks
            ]

    async def complete_task(self, user_id: str, task_id: int, completed: bool) -> Dict[str, Any]:
        """Mark a task as completed or pending"""
        from src.core.database import async_engine
        async with AsyncSession(async_engine) as session:
            task = await complete_task(session, user_id, task_id, completed)
            if task:
                return {
                    "task_id": task.id,
                    "status": "completed" if task.completed else "pending",
                    "title": task.title
                }
            else:
                return {"error": "Task not found"}

    async def delete_task(self, user_id: str, task_id: int) -> Dict[str, Any]:
        """Delete a task"""
        from src.core.database import async_engine
        async with AsyncSession(async_engine) as session:
            success = await delete_task(session, user_id, task_id)
            if success:
                return {
                    "task_id": task_id,
                    "status": "deleted"
                }
            else:
                return {"error": "Task not found"}

    async def update_task(self, user_id: str, task_id: int, title: str = None, description: str = None) -> Dict[str, Any]:
        """Update a task's details"""
        from src.core.database import async_engine
        async with AsyncSession(async_engine) as session:
            # Prepare update data
            update_data = TaskUpdate()
            if title is not None:
                update_data.title = title
            if description is not None:
                update_data.description = description

            task = await update_task(session, user_id, task_id, update_data)
            if task:
                return {
                    "task_id": task.id,
                    "status": "updated",
                    "title": task.title
                }
            else:
                return {"error": "Task not found"}


# Global MCP server instance
mcp_server = MCPServer()