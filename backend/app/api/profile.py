
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.services.profile_service import ProfileService
from app.models.profile import UserProfile
import logging
import json
import os

router = APIRouter(prefix="/api/profile", tags=["profile"])
logger = logging.getLogger(__name__)

# File-based persistence
PROFILE_FILE = "profile.json"

def load_profile() -> UserProfile:
    """Load profile from disk"""
    try:
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, "r") as f:
                data = json.load(f)
                return UserProfile(**data)
    except Exception as e:
        logger.error(f"Error loading profile: {e}")
    return UserProfile()

def save_profile(profile: UserProfile):
    """Save profile to disk"""
    try:
        with open(PROFILE_FILE, "w") as f:
            f.write(profile.model_dump_json(indent=2))
    except Exception as e:
        logger.error(f"Error saving profile: {e}")

class ProfileUpdateRequest(BaseModel):
    text: str

@router.post("/update")
async def update_profile(request: ProfileUpdateRequest) -> UserProfile:
    """Update user profile based on text input"""
    try:
        current_profile = load_profile()
        service = ProfileService()
        updated_profile = service.extract_profile(request.text, current_profile)
        save_profile(updated_profile)
        return updated_profile
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_profile() -> UserProfile:
    """Get current user profile"""
    return load_profile()

@router.delete("/")
async def clear_profile():
    """Clear user profile"""
    empty_profile = UserProfile()
    save_profile(empty_profile)
    return {"status": "success", "message": "Profile cleared"}
