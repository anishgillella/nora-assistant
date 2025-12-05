"""
Conversations API Router

Handles conversation persistence using SQLite.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import sqlite3
import json
import os

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "nora.db")


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            metadata TEXT,
            created_at TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    
    conn.commit()
    conn.close()


# Initialize on module load
init_db()


class Message(BaseModel):
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: Optional[str] = None


class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message] = []
    created_at: str
    updated_at: str


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class AddMessageRequest(BaseModel):
    role: str
    content: str
    metadata: Optional[dict] = None


@router.get("", response_model=List[Conversation])
async def list_conversations(limit: int = 20, skip: int = 0):
    """List all conversations"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, skip)
        )
        rows = cursor.fetchall()
        
        conversations = []
        for row in rows:
            conversations.append(Conversation(
                id=row["id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                messages=[]  # Don't load messages for list view
            ))
        
        conn.close()
        return conversations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation"""
    try:
        import uuid
        
        conn = get_db()
        cursor = conn.cursor()
        
        conv_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, request.title, now, now)
        )
        
        conn.commit()
        conn.close()
        
        return Conversation(
            id=conv_id,
            title=request.title,
            created_at=now,
            updated_at=now,
            messages=[]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all messages"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get conversation
        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        conv_row = cursor.fetchone()
        
        if not conv_row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        msg_rows = cursor.fetchall()
        
        messages = [
            Message(
                role=row["role"],
                content=row["content"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                created_at=row["created_at"]
            )
            for row in msg_rows
        ]
        
        conn.close()
        
        return Conversation(
            id=conv_row["id"],
            title=conv_row["title"],
            created_at=conv_row["created_at"],
            updated_at=conv_row["updated_at"],
            messages=messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/messages", response_model=Message)
async def add_message(conversation_id: str, request: AddMessageRequest):
    """Add a message to a conversation"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify conversation exists
        cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        now = datetime.now().isoformat()
        metadata_json = json.dumps(request.metadata) if request.metadata else None
        
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, request.role, request.content, metadata_json, now)
        )
        
        # Update conversation timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        
        conn.commit()
        conn.close()
        
        return Message(
            role=request.role,
            content=request.content,
            metadata=request.metadata,
            created_at=now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Delete messages first (foreign key)
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        
        # Delete conversation
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Conversation deleted"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{conversation_id}/title")
async def update_title(conversation_id: str, title: str):
    """Update conversation title"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.now().isoformat(), conversation_id)
        )
        
        conn.commit()
        conn.close()
        
        return {"status": "success", "title": title}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
