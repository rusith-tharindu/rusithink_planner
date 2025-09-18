from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib
import requests
import pandas as pd
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import aiofiles
import mimetypes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / 'uploads'
UPLOADS_DIR.mkdir(exist_ok=True)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Project Planning API")

# Mount static files for uploaded content
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security scheme (but we won't use it directly to avoid cookie issues)
security = HTTPBearer(auto_error=False)

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class UserRole(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: str  # For display (computed from first_name + last_name or OAuth name)
    phone: Optional[str] = None
    company_name: Optional[str] = None
    picture: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    registration_type: str = "oauth"  # "oauth" or "manual"
    password_hash: Optional[str] = None  # Only for manual registration
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProjectUpdate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    content: str
    created_by: str  # Admin user ID
    created_by_name: str  # Admin name for display
    is_read: bool = False  # Whether client has read this update
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None  # Optional - can be general chat or task-specific
    sender_id: str  # User ID of sender
    sender_name: str  # Name of sender for display
    sender_role: str  # "admin" or "client"
    recipient_id: str  # User ID of recipient
    content: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProjectMilestone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    title: str
    description: Optional[str] = None
    status: str = "pending"  # "pending", "in_progress", "completed"
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    created_by: str  # Admin user ID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    due_datetime: datetime
    project_price: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_by: Optional[str] = None  # User ID (optional for backward compatibility)
    client_email: Optional[str] = None  # For admin reference (optional for backward compatibility)
    client_name: Optional[str] = None   # For admin reference (optional for backward compatibility)
    unread_updates: int = 0  # Count of unread updates for client
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response Models
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_datetime: datetime
    project_price: Optional[float] = None
    priority: TaskPriority = TaskPriority.MEDIUM

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_datetime: Optional[datetime] = None
    project_price: Optional[float] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None

class ProjectUpdateCreate(BaseModel):
    content: str

class UserRegistration(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone: str
    company_name: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class SessionResponse(BaseModel):
    user: User
    session_token: str

# Helper functions
def prepare_for_mongo(data):
    """Convert datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    """Parse datetime strings back to datetime objects from MongoDB"""
    if isinstance(item, dict):
        for key, value in item.items():
            if key in ['due_datetime', 'created_at', 'updated_at', 'expires_at'] and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
    return item

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication helpers
async def get_current_user(request: Request) -> Optional[User]:
    """Get current authenticated user from session token (cookie first, then header)"""
    session_token = None
    
    # Check cookie first
    session_token = request.cookies.get("session_token")
    
    # Fall back to Authorization header if no cookie
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        logger.info("No session token found in cookies or headers")
        return None
    
    # Find session in database
    session_data = await db.sessions.find_one({"session_token": session_token})
    if not session_data:
        logger.info(f"Session not found for token: {session_token[:10]}...")
        return None
    
    session_data = parse_from_mongo(session_data)
    session = Session(**session_data)
    
    # Check if session is expired
    if session.expires_at < datetime.now(timezone.utc):
        await db.sessions.delete_one({"session_token": session_token})
        logger.info(f"Session expired for token: {session_token[:10]}...")
        return None
    
    # Get user
    user_data = await db.users.find_one({"id": session.user_id})
    if not user_data:
        logger.info(f"User not found for session user_id: {session.user_id}")
        return None
    
    user_data = parse_from_mongo(user_data)
    
    # Ensure all required fields exist for backward compatibility
    if 'first_name' not in user_data:
        user_data['first_name'] = None
    if 'last_name' not in user_data:
        user_data['last_name'] = None
    if 'phone' not in user_data:
        user_data['phone'] = None
    if 'company_name' not in user_data:
        user_data['company_name'] = None
    if 'registration_type' not in user_data:
        user_data['registration_type'] = "oauth"
    if 'password_hash' not in user_data:
        user_data['password_hash'] = None
    
    logger.info(f"User authenticated: {user_data['email']} (role: {user_data.get('role', 'unknown')})")
    return User(**user_data)

async def require_admin(request: Request) -> User:
    """Require admin role"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_auth(request: Request) -> User:
    """Require authentication"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

# Initialize database with default admin
async def init_database():
    """Initialize database with default admin account"""
    admin_exists = await db.users.find_one({"email": "admin@example.com"})
    if not admin_exists:
        admin_user = User(
            id="admin-" + str(uuid.uuid4()),
            email="admin@example.com",
            first_name="Admin",
            last_name="User", 
            name="Administrator",
            phone=None,
            company_name="RusiThink",
            role=UserRole.ADMIN,
            registration_type="admin",
            password_hash=None  # Admin doesn't use password in User model
        )
        
        admin_data = prepare_for_mongo(admin_user.dict())
        await db.users.insert_one(admin_data)
        
        # Create admin credentials entry
        admin_cred = {
            "username": "rusithink",
            "password_hash": hash_password("20200104Rh"),
            "user_id": admin_user.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.admin_credentials.insert_one(admin_cred)
        
        print("✅ Default admin account created: rusithink")

# Authentication Routes
@api_router.get("/")
async def api_root():
    """API root endpoint"""
    return {"message": "Project Planning API is running", "status": "ok"}

@api_router.post("/auth/register", response_model=SessionResponse)
async def register_user(user_data: UserRegistration, response: Response):
    """Manual user registration"""
    
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            logger.warning(f"Registration failed - email already exists: {user_data.email}")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate required fields
        if not user_data.first_name or not user_data.first_name.strip():
            logger.warning(f"Registration failed - missing first name: {user_data.email}")
            raise HTTPException(status_code=400, detail="First name is required")
        
        if not user_data.last_name or not user_data.last_name.strip():
            logger.warning(f"Registration failed - missing last name: {user_data.email}")
            raise HTTPException(status_code=400, detail="Last name is required")
        
        if not user_data.phone or not user_data.phone.strip():
            logger.warning(f"Registration failed - missing phone: {user_data.email}")
            raise HTTPException(status_code=400, detail="Phone number is required")
        
        if not user_data.company_name or not user_data.company_name.strip():
            logger.warning(f"Registration failed - missing company name: {user_data.email}")
            raise HTTPException(status_code=400, detail="Company name is required")
        
        if not user_data.password or len(user_data.password) < 6:
            logger.warning(f"Registration failed - invalid password: {user_data.email}")
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Create new user
        user = User(
            email=user_data.email.strip(),
            first_name=user_data.first_name.strip(),
            last_name=user_data.last_name.strip(),
            name=f"{user_data.first_name.strip()} {user_data.last_name.strip()}",
            phone=user_data.phone.strip(),
            company_name=user_data.company_name.strip(),
            role=UserRole.CLIENT,
            registration_type="manual",
            password_hash=hash_password(user_data.password)
        )
        
        # Save user to database
        user_dict = prepare_for_mongo(user.dict())
        await db.users.insert_one(user_dict)
        
        logger.info(f"User created successfully: {user_data.email}")
        
        # Create session
        session_token = str(uuid.uuid4()) + "-" + str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        session = Session(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        session_data = prepare_for_mongo(session.dict())
        await db.sessions.insert_one(session_data)
        
        logger.info(f"Session created for user: {user_data.email}")
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=False,  # Allow JavaScript access for debugging
            secure=False,  # Allow non-HTTPS for testing
            samesite="lax",  # Changed from "none" for better compatibility
            path="/"
        )
        
        # Return user without password hash
        user_response = user.dict()
        user_response.pop('password_hash', None)
        user_response_obj = User(**user_response)
        
        logger.info(f"Registration completed successfully: {user_data.email}")
        return SessionResponse(user=user_response_obj, session_token=session_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed with exception for {user_data.email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@api_router.post("/auth/admin-login", response_model=SessionResponse)
async def admin_login(login_data: LoginRequest, response: Response):
    """Admin login with username/password"""
    
    # Find admin credentials
    cred = await db.admin_credentials.find_one({
        "username": login_data.username,
        "password_hash": hash_password(login_data.password)
    })
    
    if not cred:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Get admin user
    user_data = await db.users.find_one({"id": cred["user_id"]})
    if not user_data:
        raise HTTPException(status_code=401, detail="Admin user not found")
    
    user_data = parse_from_mongo(user_data)
    user = User(**user_data)
    
    # Create session
    session_token = str(uuid.uuid4()) + "-" + str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = Session(
        user_id=user.id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    session_data = prepare_for_mongo(session.dict())
    await db.sessions.insert_one(session_data)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,  # 7 days
        httponly=False,  # Allow JavaScript access for debugging
        secure=False,  # Allow non-HTTPS for testing
        samesite="lax",  # Changed from "none" for better compatibility  
        path="/"
    )
    
    return SessionResponse(user=user, session_token=session_token)

@api_router.post("/auth/oauth/session-data", response_model=SessionResponse)
async def process_oauth_session(request: Request, response: Response):
    """Process OAuth session ID and create user session"""
    
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")
    
    # Call Emergent Auth API to get user data
    try:
        auth_response = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session ID")
        
        auth_data = auth_response.json()
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": auth_data["email"]})
        
        if existing_user:
            existing_user = parse_from_mongo(existing_user)
            user_dict = existing_user
            # Update name if needed
            if 'name' not in user_dict or not user_dict['name']:
                user_dict['name'] = auth_data["name"]
                
            # Ensure all required fields exist
            if 'first_name' not in user_dict:
                user_dict['first_name'] = None
            if 'last_name' not in user_dict:
                user_dict['last_name'] = None
            if 'phone' not in user_dict:
                user_dict['phone'] = None
            if 'company_name' not in user_dict:
                user_dict['company_name'] = None
            if 'registration_type' not in user_dict:
                user_dict['registration_type'] = "oauth"
            if 'password_hash' not in user_dict:
                user_dict['password_hash'] = None
        else:
            # Create new client user
            user_dict = {
                "id": str(uuid.uuid4()),
                "email": auth_data["email"],
                "name": auth_data["name"],
                "first_name": None,
                "last_name": None,
                "phone": None,
                "company_name": None,
                "picture": auth_data.get("picture"),
                "role": UserRole.CLIENT.value,
                "registration_type": "oauth",
                "password_hash": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.users.insert_one(user_dict)
        
        user = User(**user_dict)
        
        # Create session with auth_data session_token
        session_token = auth_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        session = Session(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        session_data = prepare_for_mongo(session.dict())
        await db.sessions.insert_one(session_data)
        
        # Set cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=7 * 24 * 60 * 60,
            httponly=False,  # Allow JavaScript access for debugging
            secure=False,  # Allow non-HTTPS for testing
            samesite="lax",  # Changed from "none" for better compatibility
            path="/"
        )
        
        return SessionResponse(user=user, session_token=session_token)
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@api_router.get("/auth/me", response_model=User)
async def get_current_user_info(request: Request):
    """Get current user information"""
    user = await require_auth(request)
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.sessions.delete_one({"session_token": session_token})
        response.delete_cookie(key="session_token", path="/")
    
    return {"message": "Logged out successfully"}

# Task Routes with Authorization
@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate, request: Request):
    """Create a new task (clients can create their own, admins can create for anyone)"""
    user = await require_auth(request)
    
    # Create task
    task_dict = task_data.dict()
    task_obj = Task(
        **task_dict,
        created_by=user.id,
        client_email=user.email,
        client_name=user.name
    )
    
    # Prepare for MongoDB storage
    task_mongo = prepare_for_mongo(task_obj.dict())
    
    try:
        await db.tasks.insert_one(task_mongo)
        return task_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks(request: Request):
    """Get tasks (clients see only their own, admins see all)"""
    user = await require_auth(request)
    
    try:
        if user.role == UserRole.ADMIN:
            # Admin sees all tasks
            tasks = await db.tasks.find().to_list(1000)
        else:
            # Client sees only their own tasks
            tasks = await db.tasks.find({"created_by": user.id}).to_list(1000)
        
        # Parse and handle legacy tasks
        parsed_tasks = []
        for task in tasks:
            parsed_task = parse_from_mongo(task)
            
            # Handle legacy tasks missing required fields
            if 'created_by' not in parsed_task:
                parsed_task['created_by'] = None
            if 'client_email' not in parsed_task:
                parsed_task['client_email'] = None
            if 'client_name' not in parsed_task:
                parsed_task['client_name'] = None
            
            parsed_tasks.append(Task(**parsed_task))
        
        return parsed_tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tasks: {str(e)}")

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str, request: Request):
    """Get a specific task"""
    user = await require_auth(request)
    
    try:
        task = await db.tasks.find_one({"id": task_id})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check authorization
        if user.role != UserRole.ADMIN and task["created_by"] != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        parsed_task = parse_from_mongo(task)
        return Task(**parsed_task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch task: {str(e)}")

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate, request: Request):
    """Update a task (clients can update their own, admins can update any)"""
    user = await require_auth(request)
    
    try:
        # Get existing task
        existing_task = await db.tasks.find_one({"id": task_id})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check authorization
        if user.role != UserRole.ADMIN and existing_task["created_by"] != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update fields
        update_data = task_update.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.now(timezone.utc)
        
        # Prepare for MongoDB
        update_data = prepare_for_mongo(update_data)
        
        await db.tasks.update_one({"id": task_id}, {"$set": update_data})
        
        # Return updated task
        updated_task = await db.tasks.find_one({"id": task_id})
        parsed_task = parse_from_mongo(updated_task)
        return Task(**parsed_task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    """Delete a task (only admins can delete)"""
    await require_admin(request)  # Only admins can delete
    
    try:
        result = await db.tasks.delete_one({"id": task_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

@api_router.put("/tasks/{task_id}/status", response_model=Task)
async def update_task_status(task_id: str, status: TaskStatus, request: Request):
    """Update task status"""
    user = await require_auth(request)
    
    try:
        # Check if task exists
        existing_task = await db.tasks.find_one({"id": task_id})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check authorization
        if user.role != UserRole.ADMIN and existing_task["created_by"] != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Update status
        update_data = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.tasks.update_one({"id": task_id}, {"$set": update_data})
        
        # Return updated task
        updated_task = await db.tasks.find_one({"id": task_id})
        parsed_task = parse_from_mongo(updated_task)
        return Task(**parsed_task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")

@api_router.get("/tasks/stats/overview")
async def get_task_stats(request: Request):
    """Get task statistics (based on user role)"""
    user = await require_auth(request)
    
    try:
        if user.role == UserRole.ADMIN:
            # Admin sees all task stats
            total_tasks = await db.tasks.count_documents({})
            pending_tasks = await db.tasks.count_documents({"status": "pending"})
            completed_tasks = await db.tasks.count_documents({"status": "completed"})
            overdue_tasks = await db.tasks.count_documents({"status": "overdue"})
            
            # Calculate total project value for all tasks
            pipeline = [
                {"$match": {"project_price": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": None, "total_value": {"$sum": "$project_price"}}}
            ]
        else:
            # Client sees only their own stats
            user_filter = {"created_by": user.id}
            total_tasks = await db.tasks.count_documents(user_filter)
            pending_tasks = await db.tasks.count_documents({**user_filter, "status": "pending"})
            completed_tasks = await db.tasks.count_documents({**user_filter, "status": "completed"})
            overdue_tasks = await db.tasks.count_documents({**user_filter, "status": "overdue"})
            
            # Calculate total project value for user's tasks
            pipeline = [
                {"$match": {**user_filter, "project_price": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": None, "total_value": {"$sum": "$project_price"}}}
            ]
        
        result = await db.tasks.aggregate(pipeline).to_list(1)
        total_value = result[0]["total_value"] if result else 0
        
        return {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "total_project_value": total_value,
            "user_role": user.role.value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

# Project Updates Routes
@api_router.post("/tasks/{task_id}/updates", response_model=ProjectUpdate)
async def add_project_update(task_id: str, update_data: ProjectUpdateCreate, request: Request):
    """Add project update (admin only)"""
    user = await require_admin(request)
    
    try:
        # Check if task exists
        task = await db.tasks.find_one({"id": task_id})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create update
        project_update = ProjectUpdate(
            task_id=task_id,
            content=update_data.content,
            created_by=user.id,
            created_by_name=user.name
        )
        
        # Save update to database
        update_data_mongo = prepare_for_mongo(project_update.dict())
        await db.project_updates.insert_one(update_data_mongo)
        
        # Increment unread updates count for the task
        await db.tasks.update_one(
            {"id": task_id},
            {"$inc": {"unread_updates": 1}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return project_update
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add project update: {str(e)}")

@api_router.get("/tasks/{task_id}/updates", response_model=List[ProjectUpdate])
async def get_project_updates(task_id: str, request: Request):
    """Get project updates for a task"""
    user = await require_auth(request)
    
    try:
        # Check if task exists and user has access
        task = await db.tasks.find_one({"id": task_id})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check authorization
        if user.role != UserRole.ADMIN and task.get("created_by") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get updates
        updates = await db.project_updates.find({"task_id": task_id}).sort("created_at", -1).to_list(100)
        parsed_updates = [parse_from_mongo(update) for update in updates]
        
        # If client is viewing, mark updates as read
        if user.role == UserRole.CLIENT:
            # Mark all updates as read
            await db.project_updates.update_many(
                {"task_id": task_id, "is_read": False},
                {"$set": {"is_read": True}}
            )
            
            # Reset unread count for task
            await db.tasks.update_one(
                {"id": task_id},
                {"$set": {"unread_updates": 0}}
            )
        
        return [ProjectUpdate(**update) for update in parsed_updates]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project updates: {str(e)}")

@api_router.get("/notifications/unread-count")
async def get_unread_notifications_count(request: Request):
    """Get count of unread notifications for current user"""
    user = await require_auth(request)
    
    try:
        if user.role == UserRole.CLIENT:
            # Client sees count of tasks with unread updates
            pipeline = [
                {"$match": {"created_by": user.id, "unread_updates": {"$gt": 0}}},
                {"$group": {"_id": None, "total_unread": {"$sum": "$unread_updates"}}}
            ]
            
            result = await db.tasks.aggregate(pipeline).to_list(1)
            unread_count = result[0]["total_unread"] if result else 0
            
            return {"unread_count": unread_count}
        else:
            # Admin doesn't have notifications for now
            return {"unread_count": 0}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notification count: {str(e)}")

# Admin Routes
@api_router.get("/admin/users", response_model=List[User])
async def get_all_users(request: Request):
    """Get all users (admin only)"""
    await require_admin(request)
    
    try:
        users = await db.users.find().to_list(1000)
        parsed_users = [parse_from_mongo(user) for user in users]
        
        # Remove password hashes from response
        clean_users = []
        for user_data in parsed_users:
            user_dict = user_data.copy()
            user_dict.pop('password_hash', None)
            clean_users.append(User(**user_dict))
        
        return clean_users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@api_router.put("/admin/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: UserUpdate, request: Request):
    """Update user information (admin only)"""
    await require_admin(request)
    
    try:
        # Check if user exists
        existing_user = await db.users.find_one({"id": user_id})
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check for email uniqueness if email is being updated
        if user_update.email:
            email_exists = await db.users.find_one({"email": user_update.email, "id": {"$ne": user_id}})
            if email_exists:
                raise HTTPException(status_code=400, detail="Email already exists")
        
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.now(timezone.utc)
        
        # Update name if first_name or last_name changed
        if 'first_name' in update_data or 'last_name' in update_data:
            existing_user = parse_from_mongo(existing_user)
            first_name = update_data.get('first_name', existing_user.get('first_name', ''))
            last_name = update_data.get('last_name', existing_user.get('last_name', ''))
            if first_name and last_name:
                update_data['name'] = f"{first_name} {last_name}"
        
        # Prepare for MongoDB
        update_data = prepare_for_mongo(update_data)
        
        await db.users.update_one({"id": user_id}, {"$set": update_data})
        
        # Return updated user
        updated_user = await db.users.find_one({"id": user_id})
        parsed_user = parse_from_mongo(updated_user)
        parsed_user.pop('password_hash', None)
        return User(**parsed_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@api_router.get("/admin/users/export/csv")
async def export_users_csv(request: Request):
    """Export users to CSV (admin only)"""
    await require_admin(request)
    
    try:
        users = await db.users.find().to_list(1000)
        parsed_users = [parse_from_mongo(user) for user in users]
        
        # Prepare data for CSV
        csv_data = []
        for user in parsed_users:
            csv_data.append({
                'Email': user.get('email', ''),
                'First Name': user.get('first_name', ''),
                'Last Name': user.get('last_name', ''),
                'Phone': user.get('phone', ''),
                'Company Name': user.get('company_name', ''),
                'Registration Type': user.get('registration_type', 'oauth'),
                'Role': user.get('role', 'client'),
                'Created At': user.get('created_at', '').split('T')[0] if user.get('created_at') else ''
            })
        
        # Create DataFrame and CSV
        df = pd.DataFrame(csv_data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Return CSV as streaming response
        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export CSV: {str(e)}")

@api_router.get("/admin/users/export/pdf")
async def export_users_pdf(request: Request):
    """Export users to PDF (admin only)"""
    await require_admin(request)
    
    try:
        users = await db.users.find().to_list(1000)
        parsed_users = [parse_from_mongo(user) for user in users]
        
        # Create PDF buffer
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # PDF content
        content = []
        
        # Title
        title = Paragraph("RusiThink - User Registration Report", title_style)
        content.append(title)
        content.append(Spacer(1, 20))
        
        # Prepare table data
        table_data = [['Email', 'Name', 'Phone', 'Company', 'Registration', 'Date']]
        
        for user in parsed_users:
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            if not name:
                name = user.get('name', '')
            
            created_date = ''
            if user.get('created_at'):
                try:
                    created_date = user.get('created_at').split('T')[0]
                except:
                    created_date = str(user.get('created_at', ''))[:10]
            
            table_data.append([
                user.get('email', ''),
                name,
                user.get('phone', ''),
                user.get('company_name', ''),
                user.get('registration_type', 'oauth').title(),
                created_date
            ])
        
        # Create table
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1.5*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        
        # Build PDF
        doc.build(content)
        pdf_buffer.seek(0)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=users_export.pdf"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")

@api_router.post("/admin/tasks", response_model=Task)
async def admin_create_task_for_client(task_data: TaskCreate, client_email: str, request: Request):
    """Admin creates task for a specific client"""
    await require_admin(request)
    
    # Find client user
    client_user_data = await db.users.find_one({"email": client_email})
    if not client_user_data:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client_user_data = parse_from_mongo(client_user_data)
    client_user = User(**client_user_data)
    
    # Create task for client
    task_dict = task_data.dict()
    task_obj = Task(
        **task_dict,
        created_by=client_user.id,
        client_email=client_user.email,
        client_name=client_user.name
    )
    
    # Prepare for MongoDB storage
    task_mongo = prepare_for_mongo(task_obj.dict())
    
    try:
        await db.tasks.insert_one(task_mongo)
        return task_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_database()

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()