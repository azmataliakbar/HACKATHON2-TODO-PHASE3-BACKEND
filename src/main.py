# backend/src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api import tasks, health, auth, chat
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import API routes
from src.api import tasks, health, auth, chat  # ← ADD chat here
from src.core.config import settings

# Create FastAPI app instance
app = FastAPI(
    title="Phase 3 Todo AI Chatbot",  # ← Updated title
    description="AI-powered multi-user todo application with natural language interface",  # ← Updated description
    version="0.2.0"  # ← Bump version to 0.2.0 for Phase 3
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(chat.router, prefix="/api", tags=["chat"])  # ← ADD this line
app.include_router(health.router, prefix="/api", tags=["health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

    # http://localhost:8000/api/health

    # http://localhost:8000/docs

# main.py is main agent who assign jobs to

# sub-agents:
# auth.py (Guard Agent) - Verifies Token
# tasks.py (Worker Agent) - Processes Request
# database.py (Connector Agent) - Queries DB

# what we send request/query as per form placeholder, what we want to do by --> frontend 
# we see at same frontend --> Response back to User

# 📊 Agent Workflow - Real Example
# Let's say user creates a task "Buy Groceries":
# ┌─────────────────────────────────────────────────────┐
# │ FRONTEND: User fills form                           │
# │ Title: "Buy Groceries"                              │
# │ Description: "Milk, Bread, Eggs"                    │
# │ Clicks: "Create Task" button                        │
# └────────────────┬────────────────────────────────────┘
#                  │
#                  ▼
# ┌─────────────────────────────────────────────────────┐
# │ MAIN AGENT (main.py)                                │
# │ "Incoming POST request to /api/tasks"               │
# │ "Route this to Task Agent"                          │
# └────────────────┬────────────────────────────────────┘
#                  │
#                  ▼
# ┌─────────────────────────────────────────────────────┐
# │ GATEKEEPER AGENT (middleware/auth.py)               │
# │ "Check JWT token first!"                            │
# │ "Token valid? Yes ✓"                                │
# │ "User ID: 83a37cf8-db4f-4c84..."                    │
# └────────────────┬────────────────────────────────────┘
#                  │
#                  ▼
# ┌─────────────────────────────────────────────────────┐
# │ TASK AGENT (tasks.py)                               │
# │ "Create task for this user"                         │
# │ "Prepare data: title, description, user_id"         │
# │ "Send to Database Agent"                            │
# └────────────────┬────────────────────────────────────┘
#                  │
#                  ▼
# ┌─────────────────────────────────────────────────────┐
# │ DATABASE AGENT (database.py)                        │
# │ "INSERT INTO task..."                               │
# │ "Connected to Neon PostgreSQL"                      │
# │ "Data saved! Task ID: 4"                            │
# └────────────────┬────────────────────────────────────┘
#                  │
#                  ▼
# ┌─────────────────────────────────────────────────────┐
# │ Response flows back through agents                  │
# │ Database → Task Agent → Main Agent → Frontend       │
# └────────────────┬────────────────────────────────────┘
#                  │
#                  ▼
# ┌─────────────────────────────────────────────────────┐
# │ FRONTEND: Task appears in dashboard!                │
# │ "Buy Groceries" - ID:000004 - Created!              │
# └─────────────────────────────────────────────────────┘

# Frontend (Next.js)
#                            │
#                            ▼
#                     ┌──────────────┐
#                     │  Main Agent  │ ← Orchestrator
#                     │   (main.py)  │
#                     └──────┬───────┘
#                            │
#            ┌───────────────┼───────────────┐
#            │               │               │
#            ▼               ▼               ▼
#     ┌──────────┐    ┌──────────┐   ┌──────────┐
#     │  Auth    │    │  Task    │   │  Health  │
#     │  Agent   │    │  Agent   │   │  Agent   │
#     └────┬─────┘    └────┬─────┘   └──────────┘
#          │               │
#          └───────┬───────┘
#                  │
#          ┌───────▼────────┐
#          │  Gatekeeper    │ ← JWT Verification
#          │  Agent         │
#          └───────┬────────┘
#                  │
#          ┌───────▼────────┐
#          │  Database      │ ← Neon PostgreSQL
#          │  Agent         │
#          └────────────────┘

# Full name: Test User
# Email: brandnew12345@example.com
# Password: TestPass123!@#
# Confirm Password: TestPass123!@#Email: azmat@test.com


# Email: azmat@test.com
# Password: test123

# ✅ ADD TASKS
# 1. add a task to buy groceries
# 2. create a task meeting with client
# 3. new task call dentist
# 4. remember to pick up kids from school
# 5. add task pay electricity bill
# ✅ LIST/SHOW TASKS
# 6. show me my tasks
# 7. list all tasks
# 8. what are my tasks
# 9. display my tasks
# 10. show tasks
# ✅ MARK COMPLETE
# 11. mark task 1 as complete
# 12. complete task 2
# 13. finish task 3
# 14. mark task 4 done
# 15. task 5 is done
# ✅ UPDATE TASKS
# 16. update task 1 to buy milk and bread
# 17. change task 2 to team meeting at 3pm
# 18. edit task 3 to call doctor
# 19. modify task 4 to soccer practice
# 20. update task 5 to pay water bill
# ✅ DELETE TASKS
# 21. delete task 1
# 22. remove task 2
# 23. cancel task 3
# 24. delete the task 4
# ✅ EDGE CASES
# 25. show completed tasks
# 26. show pending tasks
# 27. add a task with a very long title that tests how the UI handles overflow text in the message bubbles
# 28. update task 99 (non-existent task)
# 29. delete task 100 (non-existent task)
# 30. just say "hello" (unknown intent)

# 🧪 COMPLETE CHATBOT TEST LIST
# ✅ 1. ADD TASKS (5 tests)
# 1. add a task to buy groceries
# 2. create a task meeting with client
# 3. new task call dentist tomorrow
# 4. remember to pick up kids from school
# 5. add task pay electricity bill
# ✅ 2. LIST/SHOW TASKS (5 tests)
# 6. show me my tasks
# 7. list all tasks
# 8. what are my tasks
# 9. display my tasks
# 10. show tasks
# ✅ 3. MARK COMPLETE (5 tests)
# 11. mark task 4 as complete
# 12. complete task 7
# 13. finish task 8
# 14. task 3 is done
# 15. mark task 1 done
# ✅ 4. UPDATE TASKS (5 tests)
# 16. update task 4 to play football
# 17. change task 7 to buy milk and bread
# 18. edit task 8 to call doctor instead
# 19. modify task 3 to dentist appointment 2pm
# 20. update task 1 to grocery shopping weekend
# ✅ 5. DELETE TASKS (4 tests)
# 21. delete task 1
# 22. remove task 7
# 23. cancel task 8
# 24. delete task 3
# ✅ 6. EDGE CASES (6 tests)
# 25. update task 999 to test (non-existent)
# 26. delete task 888 (non-existent)
# 27. mark task 777 complete (non-existent)
# 28. hello (unknown intent)
# 29. what can you do? (help)
# 30. add a task with a very long title like this one that has many words to test text wrapping and overflow handling in the UI
