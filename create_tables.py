# backend/create_tables.py
import asyncio
from sqlmodel import SQLModel
from src.core.database import async_engine
from src.models import User, Task, Conversation, Message

async def create_tables():
    """Create all database tables"""
    print("🔗 Connecting to Neon PostgreSQL...")
    print("📊 Creating tables if they don't exist...")
    
    async with async_engine.begin() as conn:
        # This will create all tables defined in SQLModel
        await conn.run_sync(SQLModel.metadata.create_all)
    
    print("\n✅ Database tables ready!")
    print("   ✅ user (existing)")
    print("   ✅ task (existing)")
    print("   ✅ conversation (NEW - for chat sessions)")
    print("   ✅ message (NEW - for chat history)")
    
    await async_engine.dispose()

if __name__ == "__main__":
    print("=" * 50)
    print("Creating Phase 3 Database Tables")
    print("=" * 50)
    asyncio.run(create_tables())
    print("\n🎉 Done! You can now use the chat feature!")