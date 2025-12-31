from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid
from src.core.database import get_async_session
from src.models import ChatRequest, ChatResponse, MessageCreate, Message
from src.agent import todo_agent
from src.services.crud import (
    get_messages_for_conversation, create_message,
    create_conversation, get_conversation
)

router = APIRouter()


@router.post("/chat/{user_id}", response_model=ChatResponse)
async def chat_endpoint(
    user_id: str,
    chat_request: ChatRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Main chat endpoint that processes natural language commands
    """
    try:
        # If no conversation_id provided, create a new conversation
        conversation_id = chat_request.conversation_id
        if not conversation_id:
            conversation = await create_conversation(session, user_id)
            conversation_id = str(conversation.id)
        else:
            # Validate that the conversation exists and belongs to the user
            conv = await get_conversation(session, int(conversation_id))
            if not conv or conv.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found or does not belong to user"
                )

        # Store the user's message in the database
        user_message = MessageCreate(
            user_id=user_id,
            conversation_id=int(conversation_id),
            role="user",
            content=chat_request.message
        )
        await create_message(session, user_message)

        # Get conversation history for context (optional, for more sophisticated agents)
        # For now, we'll just pass the current message to the agent
        # In a more advanced implementation, we might fetch recent messages for context

        # Process the message with the AI agent
        response = await todo_agent.process_message(user_id, chat_request.message)

        # Store the assistant's response in the database
        assistant_message = MessageCreate(
            user_id=user_id,
            conversation_id=int(conversation_id),
            role="assistant",
            content=response.response
        )
        await create_message(session, assistant_message)

        # Update the response with the actual conversation ID
        response.conversation_id = conversation_id

        return response

    except Exception as e:
        print(f"🚨 Chat endpoint error: {str(e)}")  # Debug logging
        import traceback
        traceback.print_exc()  # Print full traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # ✅ FIXED!
            detail=f"Error processing chat request: {str(e)}"
        )


# Health check for the chat endpoint
@router.get("/chat/health")
async def chat_health():
    return {"status": "healthy", "service": "chat-endpoint"}