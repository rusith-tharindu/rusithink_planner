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
from typing import List, Optional, Dict
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

# Analytics Models
class ClientAnalytics(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    total_projects: int = 0
    completed_projects: int = 0
    pending_projects: int = 0
    total_spent: float = 0.0
    average_project_value: float = 0.0
    monthly_spending: Dict[str, float] = Field(default_factory=dict)  # "YYYY-MM": amount
    project_completion_rate: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AdminAnalytics(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    month_year: str  # Format: "YYYY-MM"
    total_revenue: float = 0.0
    total_projects: int = 0
    completed_projects: int = 0
    pending_projects: int = 0
    new_clients: int = 0
    active_clients: int = 0
    average_project_value: float = 0.0
    project_completion_rate: float = 0.0
    revenue_by_client: Dict[str, float] = Field(default_factory=dict)  # client_id: revenue
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    name: str  # For display (computed from first_name + last_name or OAuth name)
    phone: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
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
    message_type: str = "text"  # "text", "file", "image"
    file_url: Optional[str] = None  # URL to uploaded file
    file_name: Optional[str] = None  # Original filename
    file_size: Optional[int] = None  # File size in bytes
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

class ChatMessageCreate(BaseModel):
    task_id: Optional[str] = None
    content: str
    recipient_id: str

class MilestoneCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None

class UserRegistration(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone: str
    company_name: str
    address: Optional[str] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
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
            # Client sees count of tasks with unread updates + unread chat messages
            pipeline = [
                {"$match": {"created_by": user.id, "unread_updates": {"$gt": 0}}},
                {"$group": {"_id": None, "total_unread": {"$sum": "$unread_updates"}}}
            ]
            
            result = await db.tasks.aggregate(pipeline).to_list(1)
            unread_updates = result[0]["total_unread"] if result else 0
            
            # Add unread chat messages
            unread_messages = await db.chat_messages.count_documents({
                "recipient_id": user.id,
                "is_read": False
            })
            
            return {"unread_count": unread_updates + unread_messages}
        else:
            # Admin sees unread chat messages from clients
            unread_messages = await db.chat_messages.count_documents({
                "recipient_id": user.id,
                "is_read": False
            })
            return {"unread_count": unread_messages}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notification count: {str(e)}")

# Chat System Routes
@api_router.post("/chat/messages", response_model=ChatMessage)
async def send_message(message_data: ChatMessageCreate, request: Request):
    """Send a chat message"""
    user = await require_auth(request)
    
    try:
        # Get recipient user info
        recipient = await db.users.find_one({"id": message_data.recipient_id})
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        recipient = parse_from_mongo(recipient)
        
        # Create message
        message = ChatMessage(
            task_id=message_data.task_id,
            sender_id=user.id,
            sender_name=user.name,
            sender_role=user.role.value,
            recipient_id=message_data.recipient_id,
            content=message_data.content,
            message_type="text"
        )
        
        # Save to database
        message_data_mongo = prepare_for_mongo(message.dict())
        await db.chat_messages.insert_one(message_data_mongo)
        
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@api_router.post("/chat/upload")
async def upload_chat_file(
    file: UploadFile = File(...),
    recipient_id: str = Form(...),
    task_id: str = Form(None),
    content: str = Form(""),
    request: Request = None
):
    """Upload file/image for chat"""
    user = await require_auth(request)
    
    try:
        # Validate file type and size
        if file.size > 16 * 1024 * 1024:  # 16MB limit
            raise HTTPException(status_code=400, detail="File too large (max 16MB)")
        
        # Validate file format
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.heic', '.csv'}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed. Supported formats: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOADS_DIR / unique_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content_data = await file.read()
            await f.write(content_data)
        
        # Determine message type
        mime_type, _ = mimetypes.guess_type(file.filename)
        message_type = "image" if mime_type and mime_type.startswith("image/") else "file"
        
        # Create chat message with file
        message = ChatMessage(
            task_id=task_id,
            sender_id=user.id,
            sender_name=user.name,
            sender_role=user.role.value,
            recipient_id=recipient_id,
            content=content or f"Shared {message_type}: {file.filename}",
            message_type=message_type,
            file_url=f"/uploads/{unique_filename}",
            file_name=file.filename,
            file_size=file.size
        )
        
        # Save to database
        message_data_mongo = prepare_for_mongo(message.dict())
        await db.chat_messages.insert_one(message_data_mongo)
        
        return message
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@api_router.get("/chat/messages", response_model=List[ChatMessage])
async def get_chat_messages(
    request: Request, 
    task_id: Optional[str] = None, 
    client_id: Optional[str] = None,
    limit: int = 50
):
    """Get chat messages for current user"""
    user = await require_auth(request)
    
    try:
        # Build query filter based on user role and parameters
        if user.role == UserRole.ADMIN:
            if client_id:
                # Admin viewing conversation with specific client
                message_filter = {
                    "$or": [
                        {"sender_id": user.id, "recipient_id": client_id},
                        {"sender_id": client_id, "recipient_id": user.id}
                    ]
                }
            else:
                # Admin viewing all their messages
                message_filter = {
                    "$or": [
                        {"sender_id": user.id},
                        {"recipient_id": user.id}
                    ]
                }
        else:
            # CLIENT: Get all messages between client and admin
            # Find admin user
            admin_user = await db.users.find_one({"role": "admin"})
            if not admin_user:
                raise HTTPException(status_code=404, detail="Admin user not found")
            
            admin_user = parse_from_mongo(admin_user)
            admin_id = admin_user["id"]
            
            # Get conversation between client and admin
            message_filter = {
                "$or": [
                    {"sender_id": user.id, "recipient_id": admin_id},
                    {"sender_id": admin_id, "recipient_id": user.id}
                ]
            }
        
        # Add task filter if specified
        if task_id:
            message_filter["task_id"] = task_id
        
        # Get messages
        messages = await db.chat_messages.find(message_filter).sort("created_at", -1).limit(limit).to_list(limit)
        parsed_messages = [parse_from_mongo(msg) for msg in messages]
        
        # Mark messages as read if user is recipient
        await db.chat_messages.update_many(
            {"recipient_id": user.id, "is_read": False},
            {"$set": {"is_read": True}}
        )
        
        # Return in chronological order (oldest first)
        parsed_messages.reverse()
        return [ChatMessage(**msg) for msg in parsed_messages]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")

@api_router.get("/chat/conversations")
async def get_conversations(request: Request):
    """Get list of conversations for current user"""
    user = await require_auth(request)
    
    try:
        # Get unique conversation partners
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"sender_id": user.id},
                        {"recipient_id": user.id}
                    ]
                }
            },
            {
                "$group": {
                    "_id": {
                        "$cond": [
                            {"$eq": ["$sender_id", user.id]},
                            "$recipient_id",
                            "$sender_id"
                        ]
                    },
                    "last_message": {"$last": "$$ROOT"},
                    "unread_count": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$eq": ["$recipient_id", user.id]},
                                        {"$eq": ["$is_read", False]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {"$sort": {"last_message.created_at": -1}}
        ]
        
        conversations = await db.chat_messages.aggregate(pipeline).to_list(100)
        
        # Get user details for each conversation
        result = []
        for conv in conversations:
            other_user_id = conv["_id"]
            other_user_data = await db.users.find_one({"id": other_user_id})
            if other_user_data:
                other_user_data = parse_from_mongo(other_user_data)
                result.append({
                    "user_id": other_user_id,
                    "user_name": other_user_data.get("name", "Unknown"),
                    "user_role": other_user_data.get("role", "client"),
                    "last_message": parse_from_mongo(conv["last_message"]),
                    "unread_count": conv["unread_count"]
                })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversations: {str(e)}")

# Project Timeline Routes
@api_router.post("/tasks/{task_id}/milestones", response_model=ProjectMilestone)
async def add_milestone(task_id: str, milestone_data: MilestoneCreate, request: Request):
    """Add project milestone (admin only)"""
    user = await require_admin(request)
    
    try:
        # Check if task exists
        task = await db.tasks.find_one({"id": task_id})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Create milestone
        milestone = ProjectMilestone(
            task_id=task_id,
            title=milestone_data.title,
            description=milestone_data.description,
            due_date=milestone_data.due_date,
            created_by=user.id
        )
        
        # Save to database
        milestone_data_mongo = prepare_for_mongo(milestone.dict())
        await db.project_milestones.insert_one(milestone_data_mongo)
        
        return milestone
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add milestone: {str(e)}")

@api_router.get("/tasks/{task_id}/milestones", response_model=List[ProjectMilestone])
async def get_milestones(task_id: str, request: Request):
    """Get project milestones"""
    user = await require_auth(request)
    
    try:
        # Check if task exists and user has access
        task = await db.tasks.find_one({"id": task_id})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Check authorization
        if user.role != UserRole.ADMIN and task.get("created_by") != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get milestones
        milestones = await db.project_milestones.find({"task_id": task_id}).sort("created_at", 1).to_list(100)
        parsed_milestones = [parse_from_mongo(milestone) for milestone in milestones]
        
        return [ProjectMilestone(**milestone) for milestone in parsed_milestones]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch milestones: {str(e)}")

@api_router.put("/milestones/{milestone_id}/status")
async def update_milestone_status(milestone_id: str, status: str, request: Request):
    """Update milestone status (admin only)"""
    user = await require_admin(request)
    
    try:
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        if status == "completed":
            update_data["completed_date"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.project_milestones.update_one(
            {"id": milestone_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Milestone not found")
        
        return {"message": "Milestone status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update milestone: {str(e)}")

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

@api_router.delete("/admin/users/bulk")
async def delete_multiple_users(user_ids: List[str], request: Request):
    """Delete multiple users (admin only)"""
    await require_admin(request)
    
    try:
        current_user = await require_auth(request)
        deleted_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                # Check if user exists
                user = await db.users.find_one({"id": user_id})
                if not user:
                    errors.append(f"User {user_id} not found")
                    continue
                
                user = parse_from_mongo(user)
                
                # Prevent admin from deleting themselves
                if user_id == current_user.id:
                    errors.append("Cannot delete your own account")
                    continue
                
                # Prevent deleting other admin accounts
                if user.get("role") == "admin":
                    errors.append(f"Cannot delete admin account: {user.get('name', user.get('email'))}")
                    continue
                
                # Delete user's tasks
                await db.tasks.delete_many({"created_by": user_id})
                
                # Delete user's chat messages
                await db.chat_messages.delete_many({
                    "$or": [
                        {"sender_id": user_id},
                        {"recipient_id": user_id}
                    ]
                })
                
                # Delete the user
                result = await db.users.delete_one({"id": user_id})
                if result.deleted_count > 0:
                    deleted_count += 1
                
            except Exception as e:
                errors.append(f"Error deleting user {user_id}: {str(e)}")
        
        return {
            "message": f"Deleted {deleted_count} user(s)",
            "deleted_count": deleted_count,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete users: {str(e)}")

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Delete a user (admin only)"""
    await require_admin(request)
    
    try:
        # Check if user exists
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = parse_from_mongo(user)
        
        # Prevent admin from deleting themselves
        current_user = await require_auth(request)
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Prevent deleting other admin accounts
        if user.get("role") == "admin":
            raise HTTPException(status_code=400, detail="Cannot delete admin accounts")
        
        # Delete user's tasks
        await db.tasks.delete_many({"created_by": user_id})
        
        # Delete user's chat messages
        await db.chat_messages.delete_many({
            "$or": [
                {"sender_id": user_id},
                {"recipient_id": user_id}
            ]
        })
        
        # Delete the user
        result = await db.users.delete_one({"id": user_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"message": f"User {user.get('name', user.get('email'))} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

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
                'Address': user.get('address', ''),
                'Registration Type': user.get('registration_type', 'oauth'),
                'Role': user.get('role', 'client'),
                'Created At': str(user.get('created_at', '')).split('T')[0] if user.get('created_at') else ''
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
        table_data = [['Email', 'Name', 'Phone', 'Company', 'Address', 'Type', 'Date']]
        
        for user in parsed_users:
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            if not name:
                name = user.get('name', '')
            
            created_date = ''
            if user.get('created_at'):
                try:
                    created_date = str(user.get('created_at')).split('T')[0]
                except:
                    created_date = str(user.get('created_at', ''))[:10]
            
            # Truncate address for table display
            address = user.get('address', '') or ''
            if len(address) > 30:
                address = address[:30] + '...'
            
            table_data.append([
                user.get('email', ''),
                name,
                user.get('phone', ''),
                user.get('company_name', ''),
                address,
                user.get('registration_type', 'oauth').title(),
                created_date
            ])
        
        # Create table with adjusted column widths
        table = Table(table_data, colWidths=[1.8*inch, 1.2*inch, 0.8*inch, 1.2*inch, 1.2*inch, 0.6*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
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

@api_router.get("/chat/admin-info")
async def get_admin_info_for_chat(request: Request):
    """Get admin user info for chat (accessible by clients)"""
    user = await require_auth(request)
    
    try:
        # Get admin user (assuming there's only one admin)
        admin_user = await db.users.find_one({"role": "admin"})
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        admin_user = parse_from_mongo(admin_user)
        
        # Return only necessary info for chat
        return {
            "id": admin_user["id"],
            "name": admin_user.get("name", "Admin"),
            "role": admin_user["role"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get admin info: {str(e)}")

@api_router.delete("/admin/chat/message/{message_id}")
async def delete_chat_message(message_id: str, request: Request):
    """Delete a specific chat message (admin only)"""
    await require_admin(request)
    
    try:
        # Check if message exists
        message = await db.chat_messages.find_one({"id": message_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Delete the message
        result = await db.chat_messages.delete_one({"id": message_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return {"message": "Chat message deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete message: {str(e)}")

@api_router.delete("/admin/chat/conversation/{client_id}")
async def delete_chat_conversation(client_id: str, request: Request):
    """Delete entire conversation with a client (admin only)"""
    await require_admin(request)
    
    try:
        current_user = await require_auth(request)
        
        # Check if client exists
        client = await db.users.find_one({"id": client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client = parse_from_mongo(client)
        
        # Prevent deleting conversation with another admin
        if client.get("role") == "admin":
            raise HTTPException(status_code=400, detail="Cannot delete admin conversations")
        
        # Delete all messages between admin and this client
        result = await db.chat_messages.delete_many({
            "$or": [
                {"sender_id": current_user.id, "recipient_id": client_id},
                {"sender_id": client_id, "recipient_id": current_user.id}
            ]
        })
        
        deleted_count = result.deleted_count
        
        return {
            "message": f"Conversation with {client.get('name', 'client')} deleted successfully",
            "deleted_messages": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@api_router.delete("/admin/chat/bulk-delete")
async def bulk_delete_chat_messages(message_ids: List[str], request: Request):
    """Delete multiple chat messages (admin only)"""
    await require_admin(request)
    
    try:
        deleted_count = 0
        errors = []
        
        for message_id in message_ids:
            try:
                result = await db.chat_messages.delete_one({"id": message_id})
                if result.deleted_count > 0:
                    deleted_count += 1
                else:
                    errors.append(f"Message {message_id} not found")
            except Exception as e:
                errors.append(f"Error deleting message {message_id}: {str(e)}")
        
        return {
            "message": f"Deleted {deleted_count} message(s)",
            "deleted_count": deleted_count,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bulk delete messages: {str(e)}")

@api_router.get("/admin/chat/export/{client_id}")
async def export_client_chat(client_id: str, request: Request):
    """Export chat messages for a specific client as PDF (admin only)"""
    await require_admin(request)
    
    try:
        # Get client user info
        client_user = await db.users.find_one({"id": client_id})
        if not client_user:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client_user = parse_from_mongo(client_user)
        
        # Get admin user (assuming there's only one admin)
        admin_user = await db.users.find_one({"role": "admin"})
        if not admin_user:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        admin_user = parse_from_mongo(admin_user)
        
        # Fetch all messages between admin and this client
        messages = await db.chat_messages.find({
            "$or": [
                {"sender_id": client_id, "recipient_id": admin_user["id"]},
                {"sender_id": admin_user["id"], "recipient_id": client_id}
            ]
        }).sort("created_at", 1).to_list(1000)
        
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
        
        # Build PDF content
        story = []
        
        # Add title
        client_name = client_user.get('name', client_user.get('email', 'Unknown'))
        title = Paragraph(f"Chat History with {client_name}", title_style)
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Add export info
        export_info = Paragraph(
            f"<b>Client:</b> {client_name}<br/>"
            f"<b>Email:</b> {client_user.get('email', 'N/A')}<br/>"
            f"<b>Company:</b> {client_user.get('company_name', 'N/A')}<br/>"
            f"<b>Export Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC<br/>"
            f"<b>Total Messages:</b> {len(messages)}",
            styles['Normal']
        )
        story.append(export_info)
        story.append(Spacer(1, 30))
        
        # Process messages
        for i, msg in enumerate(messages):
            msg = parse_from_mongo(msg)
            
            # Format datetime
            created_at = msg.get('created_at', '')
            if isinstance(created_at, datetime):
                formatted_date = created_at.strftime('%Y-%m-%d %H:%M:%S')
            else:
                formatted_date = str(created_at)[:19]
            
            # Create message content
            sender_name = msg.get('sender_name', 'Unknown')
            sender_role = msg.get('sender_role', '').upper()
            content = msg.get('content', '')
            message_type = msg.get('message_type', 'text')
            
            # Message header
            msg_header = f"<b>{sender_name} ({sender_role})</b> - {formatted_date}"
            story.append(Paragraph(msg_header, styles['Heading3']))
            
            # Message content
            if message_type == 'file':
                file_name = msg.get('file_name', 'Unknown file')
                file_size = msg.get('file_size', 0)
                size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0
                content += f" [File: {file_name}, Size: {size_mb} MB]"
            
            msg_content = Paragraph(content, styles['Normal'])
            story.append(msg_content)
            story.append(Spacer(1, 15))
            
            # Add page break every 20 messages to avoid overcrowding
            if (i + 1) % 20 == 0 and i < len(messages) - 1:
                story.append(Spacer(1, 50))
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        
        # Prepare response
        client_name_clean = client_name.replace(' ', '_').replace('@', '_at_')
        filename = f"chat_history_{client_name_clean}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            io.BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export chat: {str(e)}")

@api_router.get("/admin/chat/conversations")
async def get_admin_chat_conversations(request: Request):
    """Get list of all client conversations for admin"""
    await require_admin(request)
    
    try:
        # Get all clients
        clients = await db.users.find({"role": "client"}).to_list(100)
        
        conversations = []
        for client in clients:
            client = parse_from_mongo(client)
            
            # Get latest message with this client
            latest_msg = await db.chat_messages.find({
                "$or": [
                    {"sender_id": client["id"]},
                    {"recipient_id": client["id"]}
                ]
            }).sort("created_at", -1).limit(1).to_list(1)
            
            # Count unread messages from this client
            unread_count = await db.chat_messages.count_documents({
                "sender_id": client["id"],
                "is_read": False
            })
            
            conversation_info = {
                "client_id": client["id"],
                "client_name": client.get("name", "Unknown"),
                "client_email": client.get("email", ""),
                "client_company": client.get("company_name", ""),
                "unread_count": unread_count,
                "last_message": None,
                "last_message_time": None
            }
            
            if latest_msg:
                msg = parse_from_mongo(latest_msg[0])
                conversation_info["last_message"] = msg.get("content", "")[:50]
                conversation_info["last_message_time"] = msg.get("created_at")
            
            conversations.append(conversation_info)
        
        # Sort by last message time (most recent first)
        conversations.sort(key=lambda x: x["last_message_time"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return conversations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversations: {str(e)}")

# Analytics calculation functions
async def calculate_client_analytics(client_id: str):
    """Calculate and update client analytics"""
    try:
        # Get all tasks for this client
        client_tasks = await db.tasks.find({"created_by": client_id}).to_list(1000)
        
        total_projects = len(client_tasks)
        completed_projects = len([task for task in client_tasks if task.get("status") == "completed"])
        pending_projects = total_projects - completed_projects
        
        # Calculate financial metrics
        total_spent = sum(task.get("project_price", 0) for task in client_tasks)
        average_project_value = total_spent / total_projects if total_projects > 0 else 0
        project_completion_rate = (completed_projects / total_projects * 100) if total_projects > 0 else 0
        
        # Calculate monthly spending
        monthly_spending = {}
        for task in client_tasks:
            task_date = task.get("created_at")
            if isinstance(task_date, str):
                task_date = datetime.fromisoformat(task_date.replace('Z', '+00:00'))
            elif isinstance(task_date, datetime):
                pass
            else:
                continue
                
            month_key = task_date.strftime("%Y-%m")
            project_price = task.get("project_price", 0)
            monthly_spending[month_key] = monthly_spending.get(month_key, 0) + project_price
        
        # Update or create client analytics
        analytics_data = {
            "client_id": client_id,
            "total_projects": total_projects,
            "completed_projects": completed_projects,
            "pending_projects": pending_projects,
            "total_spent": total_spent,
            "average_project_value": average_project_value,
            "monthly_spending": monthly_spending,
            "project_completion_rate": project_completion_rate,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Upsert analytics record
        await db.client_analytics.update_one(
            {"client_id": client_id},
            {"$set": analytics_data},
            upsert=True
        )
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate client analytics: {str(e)}")

async def calculate_admin_analytics(month_year: str = None):
    """Calculate and update admin analytics for a specific month or current month"""
    try:
        if not month_year:
            month_year = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Parse month_year to get date range
        year, month = map(int, month_year.split("-"))
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        # Get all tasks for this month
        all_tasks = await db.tasks.find({}).to_list(10000)
        month_tasks = []
        
        for task in all_tasks:
            task_date = task.get("created_at")
            if isinstance(task_date, str):
                task_date = datetime.fromisoformat(task_date.replace('Z', '+00:00'))
            elif isinstance(task_date, datetime):
                pass
            else:
                continue
                
            if start_date <= task_date < end_date:
                month_tasks.append(task)
        
        # Calculate metrics
        total_projects = len(month_tasks)
        completed_projects = len([task for task in month_tasks if task.get("status") == "completed"])
        pending_projects = total_projects - completed_projects
        total_revenue = sum(task.get("project_price", 0) for task in month_tasks)
        average_project_value = total_revenue / total_projects if total_projects > 0 else 0
        project_completion_rate = (completed_projects / total_projects * 100) if total_projects > 0 else 0
        
        # Calculate client metrics
        client_ids_this_month = set(task.get("created_by") for task in month_tasks)
        active_clients = len(client_ids_this_month)
        
        # Get new clients this month
        new_clients_count = 0
        all_users = await db.users.find({"role": "client"}).to_list(1000)
        for user in all_users:
            user_date = user.get("created_at")
            if isinstance(user_date, str):
                user_date = datetime.fromisoformat(user_date.replace('Z', '+00:00'))
            elif isinstance(user_date, datetime):
                pass
            else:
                continue
                
            if start_date <= user_date < end_date:
                new_clients_count += 1
        
        # Calculate revenue by client
        revenue_by_client = {}
        for task in month_tasks:
            client_id = task.get("created_by")
            if client_id:
                revenue_by_client[client_id] = revenue_by_client.get(client_id, 0) + task.get("project_price", 0)
        
        # Update or create admin analytics
        analytics_data = {
            "month_year": month_year,
            "total_revenue": total_revenue,
            "total_projects": total_projects,
            "completed_projects": completed_projects,
            "pending_projects": pending_projects,
            "new_clients": new_clients_count,
            "active_clients": active_clients,
            "average_project_value": average_project_value,
            "project_completion_rate": project_completion_rate,
            "revenue_by_client": revenue_by_client,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Upsert analytics record
        await db.admin_analytics.update_one(
            {"month_year": month_year},
            {"$set": analytics_data},
            upsert=True
        )
        
        return analytics_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate admin analytics: {str(e)}")

# Analytics API endpoints
@api_router.get("/analytics/client")
async def get_client_analytics(request: Request):
    """Get client analytics"""
    user = await require_auth(request)
    
    if user.role != UserRole.CLIENT:
        raise HTTPException(status_code=403, detail="Only clients can access client analytics")
    
    try:
        # Calculate fresh analytics
        analytics_data = await calculate_client_analytics(user.id)
        
        # Get historical data for trends
        analytics_record = await db.client_analytics.find_one({"client_id": user.id})
        if analytics_record:
            analytics_record = parse_from_mongo(analytics_record)
            return ClientAnalytics(**analytics_record)
        else:
            return ClientAnalytics(**analytics_data)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get client analytics: {str(e)}")

@api_router.get("/analytics/admin")
async def get_admin_analytics(request: Request, months: int = 12):
    """Get admin analytics for the last N months"""
    await require_admin(request)
    
    try:
        analytics_data = []
        current_date = datetime.now(timezone.utc)
        
        # Get analytics for the last N months
        for i in range(months):
            # Calculate date for each month going backwards
            target_date = current_date.replace(day=1)  # First day of current month
            
            # Go back i months
            year = target_date.year
            month = target_date.month - i
            
            # Handle year boundary crossing
            while month <= 0:
                month += 12
                year -= 1
            
            month_year = f"{year}-{month:02d}"
            
            # Calculate analytics for this month
            month_analytics = await calculate_admin_analytics(month_year)
            analytics_data.append(month_analytics)
        
        # Also get stored historical data
        historical_records = await db.admin_analytics.find({}).sort("month_year", -1).limit(months).to_list(months)
        
        # Merge calculated and historical data
        stored_data = {}
        for record in historical_records:
            record = parse_from_mongo(record)
            stored_data[record["month_year"]] = record
        
        # Use stored data if available, otherwise use calculated data
        final_analytics = []
        for calc_data in analytics_data:
            month_year = calc_data["month_year"]
            if month_year in stored_data:
                final_analytics.append(AdminAnalytics(**stored_data[month_year]))
            else:
                final_analytics.append(AdminAnalytics(**calc_data))
        
        return final_analytics[::-1]  # Return chronological order
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get admin analytics: {str(e)}")

@api_router.post("/analytics/calculate")
async def recalculate_analytics(request: Request):
    """Recalculate analytics for all users (admin only)"""
    await require_admin(request)
    
    try:
        # Recalculate client analytics for all clients
        clients = await db.users.find({"role": "client"}).to_list(1000)
        client_count = 0
        
        for client in clients:
            client = parse_from_mongo(client)
            await calculate_client_analytics(client["id"])
            client_count += 1
        
        # Recalculate admin analytics for last 12 months
        current_date = datetime.now(timezone.utc)
        admin_months = 0
        
        for i in range(12):
            # Calculate date for each month going backwards
            target_date = current_date.replace(day=1)  # First day of current month
            
            # Go back i months
            year = target_date.year
            month = target_date.month - i
            
            # Handle year boundary crossing
            while month <= 0:
                month += 12
                year -= 1
            
            month_year = f"{year}-{month:02d}"
            await calculate_admin_analytics(month_year)
            admin_months += 1
        
        return {
            "message": "Analytics recalculated successfully",
            "clients_processed": client_count,
            "admin_months_processed": admin_months
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to recalculate analytics: {str(e)}")

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