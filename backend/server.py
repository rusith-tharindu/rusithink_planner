from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Project Planning API")

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
    name: str
    picture: Optional[str] = None
    role: UserRole = UserRole.CLIENT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
        return None
    
    # Find session in database
    session_data = await db.sessions.find_one({"session_token": session_token})
    if not session_data:
        return None
    
    session_data = parse_from_mongo(session_data)
    session = Session(**session_data)
    
    # Check if session is expired
    if session.expires_at < datetime.now(timezone.utc):
        await db.sessions.delete_one({"session_token": session_token})
        return None
    
    # Get user
    user_data = await db.users.find_one({"id": session.user_id})
    if not user_data:
        return None
    
    user_data = parse_from_mongo(user_data)
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
            name="Administrator",
            role=UserRole.ADMIN
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
        httponly=True,
        secure=True,
        samesite="none",
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
            user = User(**existing_user)
        else:
            # Create new client user
            user = User(
                email=auth_data["email"],
                name=auth_data["name"],
                picture=auth_data.get("picture"),
                role=UserRole.CLIENT
            )
            
            user_data = prepare_for_mongo(user.dict())
            await db.users.insert_one(user_data)
        
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
            httponly=True,
            secure=True,
            samesite="none",
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

# Admin Routes
@api_router.get("/admin/users", response_model=List[User])
async def get_all_users(request: Request):
    """Get all users (admin only)"""
    await require_admin(request)
    
    try:
        users = await db.users.find().to_list(1000)
        parsed_users = [parse_from_mongo(user) for user in users]
        return [User(**user) for user in parsed_users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

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