# backend/src/agent.py
"""
AI Agent for processing natural language todo commands using Google Gemini
"""
from typing import Dict, Any, Optional, List
from src.models import ChatResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_session
from src.services.crud import (
    get_tasks, create_task, update_task, delete_task, get_task
)
from src.schemas.tasks import TaskCreate, TaskUpdate
import logging
import os
import re
import google.generativeai as genai

logger = logging.getLogger(__name__)


class TodoAgent:
    """
    AI agent that understands natural language and manages todos using Gemini AI
    """
    
    def __init__(self):
        """Initialize the agent with Gemini API"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Agent will use fallback mode.")
            self.model = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name for newer version
                logger.info("TodoAgent initialized with Gemini AI")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.model = None
    
    def _extract_intent_and_params(self, message: str, gemini_response: str) -> Dict[str, Any]:
        """
        Parse Gemini's response to extract intent and parameters
        """
        intent_mapping = {
            "ADD": "add_task",
            "LIST": "list_tasks", 
            "SHOW": "list_tasks",
            "GET": "list_tasks",
            "COMPLETE": "complete_task",
            "MARK": "complete_task",
            "DELETE": "delete_task",
            "REMOVE": "delete_task",
            "UPDATE": "update_task",
            "EDIT": "update_task",
            "MODIFY": "update_task"
        }
        
        # Default response
        result = {
            "intent": "unknown",
            "params": {},
            "task_title": "",
            "task_id": None
        }
        
        # Parse the response line by line
        lines = gemini_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract intent
            if line.startswith("INTENT:"):
                intent_str = line.replace("INTENT:", "").strip().upper()
                for key in intent_mapping:
                    if key in intent_str:
                        result["intent"] = intent_mapping[key]
                        break
            
            # Extract task title
            elif line.startswith("TITLE:"):
                result["task_title"] = line.replace("TITLE:", "").strip()
            
            # Extract task ID
            elif line.startswith("TASK_ID:"):
                task_id_str = line.replace("TASK_ID:", "").strip()
                # Extract numbers from the string
                numbers = re.findall(r'\d+', task_id_str)
                if numbers:
                    result["task_id"] = int(numbers[0])
            
            # Extract description
            elif line.startswith("DESCRIPTION:"):
                result["params"]["description"] = line.replace("DESCRIPTION:", "").strip()
            
            # Extract completed status
            elif line.startswith("COMPLETED:"):
                completed_str = line.replace("COMPLETED:", "").strip().lower()
                result["params"]["completed"] = completed_str in ["true", "yes", "1"]
        
        return result
    
    async def _get_gemini_intent(self, message: str) -> str:
        """
        Use Gemini to understand user intent
        """
        if not self.model:
            return self._fallback_intent(message)
        
        prompt = f"""You are a todo assistant. Analyze this message and extract the intent and parameters.

User message: "{message}"

Respond in this exact format:
INTENT: [ADD/LIST/COMPLETE/DELETE/UPDATE]
TITLE: [task title if adding/updating]
TASK_ID: [task number/ID if completing/deleting/updating]
DESCRIPTION: [any additional details]
COMPLETED: [true/false if marking complete]

Examples:
- "add a task to buy groceries" -> INTENT: ADD, TITLE: buy groceries
- "show me my tasks" -> INTENT: LIST
- "mark task 5 as complete" -> INTENT: COMPLETE, TASK_ID: 5
- "delete task 3" -> INTENT: DELETE, TASK_ID: 3
- "update task 2 to call mom tonight" -> INTENT: UPDATE, TASK_ID: 2, TITLE: call mom tonight

Now analyze: "{message}"
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_intent(message)
    
    def _fallback_intent(self, message: str) -> str:
        """
        Fallback keyword-based intent detection
        """
        message_lower = message.lower()
        
        # Check for update/edit/modify/change first (more specific)
        if any(word in message_lower for word in ["update", "change", "edit", "modify"]):
            numbers = re.findall(r'\d+', message)
            task_id = numbers[0] if numbers else ""
            # Extract text after "to" or after task number
            title = ""
            if " to " in message_lower:
                title = message.split(" to ", 1)[1].strip()
            elif task_id:
                # Remove everything up to and including the task number
                title = re.sub(rf'.*?{task_id}\s*', '', message, count=1).strip()
            return f"INTENT: UPDATE\nTASK_ID: {task_id}\nTITLE: {title}"
        
        elif any(word in message_lower for word in ["complete", "done", "finish", "mark"]):
            # Try to extract task ID
            numbers = re.findall(r'\d+', message)
            task_id = numbers[0] if numbers else ""
            return f"INTENT: COMPLETE\nTASK_ID: {task_id}"
        
        elif any(word in message_lower for word in ["delete", "remove", "cancel"]):
            numbers = re.findall(r'\d+', message)
            task_id = numbers[0] if numbers else ""
            return f"INTENT: DELETE\nTASK_ID: {task_id}"
        
        elif any(word in message_lower for word in ["add", "create", "new", "remember"]):
            # Try to extract task title
            title = message
            for word in ["add", "create", "new", "remember", "task", "a"]:
                title = re.sub(rf'\b{word}\b', '', title, flags=re.IGNORECASE)
            # Also check for "to" pattern like "add a task to buy milk"
            if " to " in message_lower:
                title = message.split(" to ", 1)[1].strip()
            else:
                title = title.strip()
            return f"INTENT: ADD\nTITLE: {title}"
        
        elif any(word in message_lower for word in ["list", "show", "what", "display", "all", "tasks"]):
            return "INTENT: LIST"
        
        return "INTENT: UNKNOWN"
    
    async def _handle_add_task(
        self, 
        user_id: str, 
        task_title: str,
        session: AsyncSession
    ) -> str:
        """Add a new task"""
        try:
            if not task_title:
                return "I need to know what task you want to add. Please specify a task title."
            
            task_data = TaskCreate(
                title=task_title,
                description="",
                completed=False
            )
            
            new_task = await create_task(session, user_id, task_data)
            return f"✅ Task added successfully!\n\nTask ID: {new_task.id}\nTitle: {new_task.title}"
        
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return f"Sorry, I couldn't add the task. Error: {str(e)}"
    
    async def _handle_list_tasks(
        self,
        user_id: str,
        session: AsyncSession
    ) -> str:
        """List all user tasks with enhanced formatting"""
        try:
            tasks = await get_tasks(session, user_id)
            
            if not tasks:
                return "You don't have any tasks yet. Try adding one by saying 'Add a task to...'"
            
            # Separate completed and pending tasks
            pending = [t for t in tasks if not t.completed]
            completed = [t for t in tasks if t.completed]
            
            response = "📋 **YOUR TASKS**\n\n"
            
            if pending:
                response += "🔵 **PENDING TASKS**\n"
                response += "━━━━━━━━━━━━━━━━━\n\n"
                for task in pending:
                    # Format: 8-digit ID (padded)
                    task_id = f"{task.id:08d}"
                    # Format date nicely
                    created = task.created_at.strftime("%b %d, %Y • %I:%M %p") if hasattr(task, 'created_at') and task.created_at else "N/A"
                    
                    response += f"✨ **{task.title}**\n"
                    if task.description and task.description.strip():
                        response += f"   📝 {task.description}\n"
                    response += f"   🆔 **ID: {task_id}**  |  📅 **{created}**\n\n"
            
            if completed:
                response += "\n✅ **COMPLETED TASKS**\n"
                response += "━━━━━━━━━━━━━━━━━\n\n"
                for task in completed:
                    task_id = f"{task.id:08d}"
                    created = task.created_at.strftime("%b %d, %Y") if hasattr(task, 'created_at') and task.created_at else "N/A"
                    completed_date = task.completed_at.strftime("%b %d, %Y") if hasattr(task, 'completed_at') and task.completed_at else "N/A"
                    
                    response += f"✓ ~~{task.title}~~\n"
                    if task.description and task.description.strip():
                        response += f"   📝 {task.description}\n"
                    response += f"   🆔 **ID: {task_id}**  |  📅 **{created}**  |  ✅ **Done: {completed_date}**\n\n"
            
            response += f"\n━━━━━━━━━━━━━━━━━\n📊 **SUMMARY**: {len(tasks)} total • {len(pending)} pending • {len(completed)} completed"
            
            return response
        
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return f"Sorry, I couldn't retrieve your tasks. Error: {str(e)}"
    
    async def _handle_complete_task(
        self,
        user_id: str,
        task_id: Optional[int],
        session: AsyncSession
    ) -> str:
        """Mark a task as complete"""
        try:
            if not task_id:
                return "Please specify which task to mark as complete (e.g., 'mark task 3 as complete')"
            
            # Get the task first to verify it exists and belongs to user
            task = await get_task(session, user_id, task_id)
            if not task:
                return f"Task {task_id} not found or doesn't belong to you."
            
            if task.completed:
                return f"Task {task_id} '{task.title}' is already completed!"
            
            # Update task
            task_update = TaskUpdate(completed=True)
            updated_task = await update_task(session, user_id, task_id, task_update)
            
            return f"✅ Task {task_id} marked as complete!\n\n'{updated_task.title}' is now done. Great job! 🎉"
        
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return f"Sorry, I couldn't mark the task as complete. Error: {str(e)}"
    
    async def _handle_delete_task(
        self,
        user_id: str,
        task_id: Optional[int],
        session: AsyncSession
    ) -> str:
        """Delete a task"""
        try:
            if not task_id:
                return "Please specify which task to delete (e.g., 'delete task 3')"
            
            # Get the task first to show what we're deleting
            task = await get_task(session, user_id, task_id)
            if not task:
                return f"Task {task_id} not found or doesn't belong to you."
            
            task_title = task.title
            
            # Delete the task
            success = await delete_task(session, user_id, task_id)
            
            if success:
                return f"🗑️ Task {task_id} '{task_title}' has been deleted."
            else:
                return f"Failed to delete task {task_id}."
        
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return f"Sorry, I couldn't delete the task. Error: {str(e)}"
    
    async def _handle_update_task(
        self,
        user_id: str,
        task_id: Optional[int],
        task_title: str,
        session: AsyncSession
    ) -> str:
        """Update a task"""
        try:
            if not task_id:
                return "Please specify which task to update (e.g., 'update task 3 to call mom')"
            
            if not task_title:
                return "Please specify what you want to update the task to."
            
            # Get the task first
            task = await get_task(session, user_id, task_id)
            if not task:
                return f"Task {task_id} not found or doesn't belong to you."
            
            # Save the old title BEFORE updating
            old_title = task.title
            
            # Clean up the title (remove common words)
            cleaned_title = task_title
            for word in ["update", "task", "to", str(task_id), "change", "edit", "modify"]:
                cleaned_title = re.sub(rf'\b{word}\b', '', cleaned_title, flags=re.IGNORECASE)
            cleaned_title = cleaned_title.strip()
            
            # Update task
            task_update = TaskUpdate(title=cleaned_title)
            updated_task = await update_task(session, user_id, task_id, task_update)
            
            return f"✏️ Task {task_id} updated!\n\nOld: '{old_title}'\nNew: '{updated_task.title}'"
        
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return f"Sorry, I couldn't update the task. Error: {str(e)}"
    
    async def process_message(self, user_id: str, message: str) -> ChatResponse:
        """
        Process a natural language message and execute the appropriate action
        
        Args:
            user_id: The user's ID
            message: Natural language message from user
            
        Returns:
            ChatResponse with agent's reply and tool calls
        """
        try:
            # Get database session
            async for session in get_async_session():
                # Use Gemini to understand intent
                gemini_response = await self._get_gemini_intent(message)
                logger.info(f"Gemini response: {gemini_response}")
                
                # Parse the response
                parsed = self._extract_intent_and_params(message, gemini_response)
                intent = parsed["intent"]
                
                # Execute the appropriate action
                if intent == "add_task":
                    response_text = await self._handle_add_task(
                        user_id, parsed["task_title"], session
                    )
                    tool_calls = ["add_task"]
                
                elif intent == "list_tasks":
                    response_text = await self._handle_list_tasks(user_id, session)
                    tool_calls = ["list_tasks"]
                
                elif intent == "complete_task":
                    response_text = await self._handle_complete_task(
                        user_id, parsed["task_id"], session
                    )
                    tool_calls = ["complete_task"]
                
                elif intent == "delete_task":
                    response_text = await self._handle_delete_task(
                        user_id, parsed["task_id"], session
                    )
                    tool_calls = ["delete_task"]
                
                elif intent == "update_task":
                    response_text = await self._handle_update_task(
                        user_id, parsed["task_id"], parsed["task_title"], session
                    )
                    tool_calls = ["update_task"]
                
                else:
                    response_text = """I can help you manage your tasks! Try:

• "Add a task to buy groceries"
• "Show me all my tasks"  
• "Mark task 5 as complete"
• "Delete task 3"
• "Update task 2 to call mom tonight"

What would you like to do?"""
                    tool_calls = []
                
                return ChatResponse(
                    conversation_id="",
                    response=response_text,
                    tool_calls=tool_calls
                )
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            return ChatResponse(
                conversation_id="",
                response=f"I'm sorry, I encountered an error: {str(e)}",
                tool_calls=[]
            )


# Create singleton instance
todo_agent = TodoAgent()