from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# Define Models
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    due_datetime: datetime
    project_price: Optional[float] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
            if key in ['due_datetime', 'created_at', 'updated_at'] and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
    return item

# Routes
@api_router.get("/")
async def root():
    return {"message": "Project Planning API is running"}

@api_router.post("/tasks", response_model=Task)
async def create_task(task_data: TaskCreate):
    task_dict = task_data.dict()
    task_obj = Task(**task_dict)
    
    # Prepare for MongoDB storage
    task_mongo = prepare_for_mongo(task_obj.dict())
    
    try:
        await db.tasks.insert_one(task_mongo)
        return task_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@api_router.get("/tasks", response_model=List[Task])
async def get_tasks():
    try:
        tasks = await db.tasks.find().to_list(1000)
        parsed_tasks = [parse_from_mongo(task) for task in tasks]
        return [Task(**task) for task in parsed_tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tasks: {str(e)}")

@api_router.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    try:
        task = await db.tasks.find_one({"id": task_id})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        parsed_task = parse_from_mongo(task)
        return Task(**parsed_task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch task: {str(e)}")

@api_router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate):
    try:
        # Get existing task
        existing_task = await db.tasks.find_one({"id": task_id})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
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
async def delete_task(task_id: str):
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
async def update_task_status(task_id: str, status: TaskStatus):
    try:
        # Check if task exists
        existing_task = await db.tasks.find_one({"id": task_id})
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
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
async def get_task_stats():
    try:
        total_tasks = await db.tasks.count_documents({})
        pending_tasks = await db.tasks.count_documents({"status": "pending"})
        completed_tasks = await db.tasks.count_documents({"status": "completed"})
        overdue_tasks = await db.tasks.count_documents({"status": "overdue"})
        
        # Calculate total project value
        pipeline = [
            {"$match": {"project_price": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": None, "total_value": {"$sum": "$project_price"}}}
        ]
        
        result = await db.tasks.aggregate(pipeline).to_list(1)
        total_value = result[0]["total_value"] if result else 0
        
        return {
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "total_project_value": total_value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()