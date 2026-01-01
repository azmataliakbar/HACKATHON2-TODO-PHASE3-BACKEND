# backend/src/agent.py
"""
AI Agent for processing natural language todo commands using Google Gemini
"""
from typing import Dict, Any, Optional, List, Tuple
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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logging.warning("google.generativeai not installed. Agent will use fallback mode.")

logger = logging.getLogger(__name__)


class TodoAgent:
    """
    AI agent that understands natural language and manages todos using Gemini AI
    """
    
    def __init__(self):
        """Initialize the agent with Gemini API"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment. Agent will use fallback mode.")
        elif not GENAI_AVAILABLE:
            logger.warning("google.generativeai package not available. Agent will use fallback mode.")
        else:
            self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini model"""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
            logger.info("✅ TodoAgent initialized with Gemini AI successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None
    
    def _parse_intent_line(self, line: str, result: Dict[str, Any]):
        """Parse a single line from Gemini response"""
        intent_mapping = {
            "ADD": "add_task", "LIST": "list_tasks", "SHOW": "list_tasks",
            "GET": "list_tasks", "COMPLETE": "complete_task", "MARK": "complete_task",
            "DELETE": "delete_task", "REMOVE": "delete_task", "UPDATE": "update_task",
            "EDIT": "update_task", "MODIFY": "update_task"
        }
        
        line = line.strip()
        
        if line.startswith("INTENT:"):
            intent_str = line.replace("INTENT:", "").strip().upper()
            for key, value in intent_mapping.items():
                if key in intent_str:
                    result["intent"] = value
                    break
        
        elif line.startswith("TITLE:"):
            result["task_title"] = line.replace("TITLE:", "").strip()
        
        elif line.startswith("TASK_ID:"):
            task_id_str = line.replace("TASK_ID:", "").strip()
            numbers = re.findall(r'\d+', task_id_str)
            if numbers:
                result["task_id"] = int(numbers[0])
        
        elif line.startswith("DESCRIPTION:"):
            result["params"]["description"] = line.replace("DESCRIPTION:", "").strip()
        
        elif line.startswith("COMPLETED:"):
            completed_str = line.replace("COMPLETED:", "").strip().lower()
            result["params"]["completed"] = completed_str in ["true", "yes", "1"]
    
    def _extract_intent_and_params(self, gemini_response: str) -> Dict[str, Any]:
        """Parse Gemini's response to extract intent and parameters"""
        result = {
            "intent": "unknown",
            "params": {},
            "task_title": "",
            "task_id": None
        }
        
        lines = gemini_response.strip().split('\n')
        for line in lines:
            self._parse_intent_line(line, result)
        
        return result
    
    async def _get_gemini_intent(self, message: str) -> str:
        """Use Gemini to understand user intent"""
        if not self.model:
            return self._fallback_intent(message)
        
        prompt = self._build_gemini_prompt(message)
        
        try:
            response = await self._call_gemini_async(prompt)
            return response
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_intent(message)
    
    async def _call_gemini_async(self, prompt: str) -> str:
        """Make async call to Gemini API"""
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self.model.generate_content(prompt)
        )
        return response.text
    
    def _build_gemini_prompt(self, message: str) -> str:
        """Build prompt for Gemini"""
        return f"""You are a todo assistant. Analyze this message and extract the intent and parameters.

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
    
    def _detect_update_intent(self, message_lower: str, message: str) -> str:
        """Detect update/edit intent"""
        numbers = re.findall(r'\d+', message)
        task_id = numbers[0] if numbers else ""
        
        title = self._extract_update_title(message, message_lower, task_id)
        return f"INTENT: UPDATE\nTASK_ID: {task_id}\nTITLE: {title}"
    
    def _extract_update_title(self, message: str, message_lower: str, task_id: str) -> str:
        """Extract title for update operation"""
        if " to " in message_lower:
            return message.split(" to ", 1)[1].strip()
        elif task_id:
            return re.sub(rf'.*?{task_id}\s*', '', message, count=1).strip()
        return ""
    
    def _detect_complete_intent(self, message: str) -> str:
        """Detect complete/done intent"""
        numbers = re.findall(r'\d+', message)
        task_id = numbers[0] if numbers else ""
        return f"INTENT: COMPLETE\nTASK_ID: {task_id}"
    
    def _detect_delete_intent(self, message: str) -> str:
        """Detect delete/remove intent"""
        numbers = re.findall(r'\d+', message)
        task_id = numbers[0] if numbers else ""
        return f"INTENT: DELETE\nTASK_ID: {task_id}"
    
    def _detect_add_intent(self, message: str, message_lower: str) -> str:
        """Detect add/create intent"""
        title = message
        for word in ["add", "create", "new", "remember", "task", "a"]:
            title = re.sub(rf'\b{word}\b', '', title, flags=re.IGNORECASE)
        
        if " to " in message_lower:
            title = message.split(" to ", 1)[1].strip()
        else:
            title = title.strip()
        
        # Remove extra quotes
        title = title.strip('"').strip("'").strip()
        
        return f"INTENT: ADD\nTITLE: {title}"
    
    def _fallback_intent(self, message: str) -> str:
        """Fallback keyword-based intent detection"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["update", "change", "edit", "modify"]):
            return self._detect_update_intent(message_lower, message)
        
        elif any(word in message_lower for word in ["complete", "done", "finish", "mark"]):
            return self._detect_complete_intent(message)
        
        elif any(phrase in message_lower for phrase in ["get rid of", "get rid", "delete", "remove", "cancel", "erase", "trash", "discard"]):
            return self._detect_delete_intent(message)
        
        elif any(word in message_lower for word in ["add", "create", "new", "remember"]):
            return self._detect_add_intent(message, message_lower)
        
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
            
            # Clean up title - remove extra quotes
            cleaned_title = task_title.strip().strip('"').strip("'").strip()
            
            task_data = TaskCreate(
                title=cleaned_title,
                description="",
                completed=False
            )
            
            new_task = await create_task(session, user_id, task_data)
            return f"✅ Task added successfully!\n\nTask ID: {new_task.id}\nTitle: {new_task.title}"
        
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return f"Sorry, I couldn't add the task. Error: {str(e)}"
    
    def _format_pending_task(self, task) -> str:
        """Format a single pending task"""
        task_id = f"{task.id:08d}"
        created = task.created_at.strftime("%b %d, %Y • %I:%M %p") if hasattr(task, 'created_at') and task.created_at else "N/A"
        
        result = f"✨ **{task.title}**\n"
        if task.description and task.description.strip():
            result += f"   📝 {task.description}\n"
        result += f"   🆔 **ID: {task_id}**  |  📅 **{created}**\n\n"
        return result
    
    def _format_completed_task(self, task) -> str:
        """Format a single completed task"""
        task_id = f"{task.id:08d}"
        created = task.created_at.strftime("%b %d, %Y") if hasattr(task, 'created_at') and task.created_at else "N/A"
        completed_date = task.completed_at.strftime("%b %d, %Y") if hasattr(task, 'completed_at') and task.completed_at else "N/A"
        
        result = f"✓ ~~{task.title}~~\n"
        if task.description and task.description.strip():
            result += f"   📝 {task.description}\n"
        result += f"   🆔 **ID: {task_id}**  |  📅 **{created}**  |  ✅ **Done: {completed_date}**\n\n"
        return result
    
    def _build_task_list_response(self, pending: List, completed: List) -> str:
        """Build formatted response for task list"""
        response = "📋 **YOUR TASKS**\n\n"
        
        if pending:
            response += "🔵 **PENDING TASKS**\n━━━━━━━━━━━━━━━━━\n\n"
            for task in pending:
                response += self._format_pending_task(task)
        
        if completed:
            response += "\n✅ **COMPLETED TASKS**\n━━━━━━━━━━━━━━━━━\n\n"
            for task in completed:
                response += self._format_completed_task(task)
        
        total = len(pending) + len(completed)
        response += f"\n━━━━━━━━━━━━━━━━━\n📊 **SUMMARY**: {total} total • {len(pending)} pending • {len(completed)} completed"
        return response
    
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
            
            pending = [t for t in tasks if not t.completed]
            completed = [t for t in tasks if t.completed]
            
            return self._build_task_list_response(pending, completed)
        
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
            
            task = await get_task(session, user_id, task_id)
            if not task:
                return f"Task {task_id} not found or doesn't belong to you."
            
            if task.completed:
                return f"Task {task_id} '{task.title}' is already completed!"
            
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
            
            task = await get_task(session, user_id, task_id)
            if not task:
                return f"Task {task_id} not found or doesn't belong to you."
            
            task_title = task.title
            success = await delete_task(session, user_id, task_id)
            
            if success:
                return f"🗑️ Task {task_id} '{task_title}' has been deleted."
            else:
                return f"Failed to delete task {task_id}."
        
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return f"Sorry, I couldn't delete the task. Error: {str(e)}"
    
    def _clean_task_title(self, task_title: str, task_id: Optional[int]) -> str:
        """Clean up task title by removing command words and extra quotes"""
        cleaned_title = task_title
        for word in ["update", "task", "to", str(task_id), "change", "edit", "modify"]:
            cleaned_title = re.sub(rf'\b{word}\b', '', cleaned_title, flags=re.IGNORECASE)
        # Remove extra quotes and whitespace
        cleaned_title = cleaned_title.strip().strip('"').strip("'").strip()
        return cleaned_title
    
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
            
            task = await get_task(session, user_id, task_id)
            if not task:
                return f"Task {task_id} not found or doesn't belong to you."
            
            old_title = task.title
            cleaned_title = self._clean_task_title(task_title, task_id)
            
            task_update = TaskUpdate(title=cleaned_title)
            updated_task = await update_task(session, user_id, task_id, task_update)
            
            return f"✏️ Task {task_id} updated!\n\nOld: '{old_title}'\nNew: '{updated_task.title}'"
        
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return f"Sorry, I couldn't update the task. Error: {str(e)}"
    
    def _get_help_message(self) -> str:
        """Return help message for unknown intents"""
        return """I can help you manage your tasks! Try:

• "Add a task to buy groceries"
• "Show me all my tasks"  
• "Mark task 5 as complete"
• "Delete task 3"
• "Update task 2 to call mom tonight"

What would you like to do?"""
    
    async def _execute_intent(
        self, 
        intent: str, 
        parsed: Dict[str, Any], 
        user_id: str, 
        session: AsyncSession
    ) -> Tuple[str, List[str]]:
        """Execute the appropriate action based on intent"""
        intent_handlers = {
            "add_task": (self._handle_add_task, [user_id, parsed["task_title"], session], ["add_task"]),
            "list_tasks": (self._handle_list_tasks, [user_id, session], ["list_tasks"]),
            "complete_task": (self._handle_complete_task, [user_id, parsed["task_id"], session], ["complete_task"]),
            "delete_task": (self._handle_delete_task, [user_id, parsed["task_id"], session], ["delete_task"]),
            "update_task": (self._handle_update_task, [user_id, parsed["task_id"], parsed["task_title"], session], ["update_task"]),
        }
        
        if intent in intent_handlers:
            handler, args, tool_calls = intent_handlers[intent]
            response_text = await handler(*args)
            return response_text, tool_calls
        
        return self._get_help_message(), []
    
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
            async for session in get_async_session():
                gemini_response = await self._get_gemini_intent(message)
                logger.info(f"Gemini response: {gemini_response}")
                
                parsed = self._extract_intent_and_params(gemini_response)
                intent = parsed["intent"]
                
                response_text, tool_calls = await self._execute_intent(
                    intent, parsed, user_id, session
                )
                
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