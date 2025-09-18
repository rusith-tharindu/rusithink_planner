import React, { useState, useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Textarea } from "./components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Badge } from "./components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "./components/ui/dialog";
import { CalendarDays, Clock, DollarSign, Plus, CheckCircle, AlertCircle, Timer, Trash2, LogOut, User, Shield, Users } from "lucide-react";
import { format } from "date-fns";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = React.createContext();

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(response.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (userData) => {
    setUser(userData);
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(null);
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

// OAuth Session Handler Component
const OAuthHandler = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const processOAuth = async () => {
      const hash = location.hash;
      const params = new URLSearchParams(hash.substring(1));
      const sessionId = params.get('session_id');

      if (sessionId && !processing) {
        setProcessing(true);
        
        try {
          const response = await axios.post(
            `${API}/auth/oauth/session-data`,
            {},
            {
              headers: { 'X-Session-ID': sessionId },
              withCredentials: true
            }
          );

          await login(response.data.user);
          
          // Clean URL
          window.history.replaceState({}, document.title, location.pathname);
          
          toast.success(`Welcome ${response.data.user.name}!`);
          navigate('/dashboard');
          
        } catch (error) {
          console.error('OAuth processing error:', error);
          toast.error('Authentication failed');
          navigate('/login');
        }
      }
    };

    processOAuth();
  }, [location, navigate, login, processing]);

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center">
        <div className="loading-spinner mx-auto mb-4"></div>
        <p className="text-slate-400">Processing authentication...</p>
      </div>
    </div>
  );
};

// Login Component
const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [adminLogin, setAdminLogin] = useState({ username: '', password: '' });
  const [showAdminLogin, setShowAdminLogin] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleOAuthLogin = () => {
    const redirectUrl = encodeURIComponent(`${window.location.origin}/dashboard`);
    window.location.href = `https://auth.emergentagent.com/?redirect=${redirectUrl}`;
  };

  const handleAdminLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/admin-login`, adminLogin, { withCredentials: true });
      await login(response.data.user);
      toast.success(`Welcome Admin ${response.data.user.name}!`);
      navigate('/dashboard');
    } catch (error) {
      toast.error('Invalid admin credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img 
              src="https://customer-assets.emergentagent.com/job_taskmaster-pro-11/artifacts/shvxprc6_Rusithink_logo.webp" 
              alt="RusiThink Logo" 
              className="h-16 w-auto"
            />
          </div>
          <h2 className="text-3xl font-bold text-slate-100 mb-2">RusiThink</h2>
          <p className="text-slate-400">Sign in to manage your projects</p>
        </div>

        <Card className="bg-slate-900/50 border-slate-700/30">
          <CardHeader>
            <CardTitle className="text-slate-100">Sign In to RusiThink</CardTitle>
            <CardDescription className="text-slate-400">
              Choose your sign-in method
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {!showAdminLogin ? (
              <>
                <Button 
                  onClick={handleOAuthLogin}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                  size="lg"
                >
                  <User className="w-5 h-5 mr-2" />
                  Sign in with Google
                </Button>
                
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-slate-600" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-slate-900 px-2 text-slate-400">Or</span>
                  </div>
                </div>
                
                <Button
                  onClick={() => setShowAdminLogin(true)}
                  variant="outline"
                  className="w-full border-slate-600 text-slate-200 hover:bg-slate-800"
                  size="lg"
                >
                  <Shield className="w-5 h-5 mr-2" />
                  Admin Login
                </Button>
              </>
            ) : (
              <form onSubmit={handleAdminLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-slate-200">Username</Label>
                  <Input
                    id="username"
                    type="text"
                    value={adminLogin.username}
                    onChange={(e) => setAdminLogin({...adminLogin, username: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-200">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={adminLogin.password}
                    onChange={(e) => setAdminLogin({...adminLogin, password: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                  />
                </div>
                
                <div className="flex gap-3">
                  <Button 
                    type="submit" 
                    disabled={loading}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                  >
                    {loading ? 'Signing in...' : 'Admin Sign In'}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => setShowAdminLogin(false)}
                    variant="outline"
                    className="border-slate-600 text-slate-200"
                  >
                    Back
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Countdown Timer Component
const CountdownTimer = ({ dueDateTime, status }) => {
  const [timeRemaining, setTimeRemaining] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
    isOverdue: false
  });

  useEffect(() => {
    const calculateTimeRemaining = () => {
      const now = new Date().getTime();
      const dueTime = new Date(dueDateTime).getTime();
      const difference = dueTime - now;

      if (difference <= 0) {
        setTimeRemaining({
          days: 0,
          hours: 0,
          minutes: 0,
          seconds: 0,
          isOverdue: true
        });
        return;
      }

      const days = Math.floor(difference / (1000 * 60 * 60 * 24));
      const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((difference % (1000 * 60)) / 1000);

      setTimeRemaining({
        days,
        hours,
        minutes,
        seconds,
        isOverdue: false
      });
    };

    calculateTimeRemaining();
    const interval = setInterval(calculateTimeRemaining, 1000);

    return () => clearInterval(interval);
  }, [dueDateTime]);

  if (status === 'completed') {
    return (
      <div className="bg-green-900/20 border border-green-700/30 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-400">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">Task Completed</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg p-4 border ${
      timeRemaining.isOverdue 
        ? 'bg-red-900/20 border-red-700/30' 
        : 'bg-slate-800/50 border-slate-700/30'
    }`}>
      <div className="flex items-center gap-2 mb-3">
        <Timer className={`w-5 h-5 ${timeRemaining.isOverdue ? 'text-red-400' : 'text-blue-400'}`} />
        <span className={`font-medium ${timeRemaining.isOverdue ? 'text-red-400' : 'text-slate-200'}`}>
          {timeRemaining.isOverdue ? 'OVERDUE' : 'Time Remaining'}
        </span>
      </div>
      
      <div className="grid grid-cols-4 gap-2">
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono ${
            timeRemaining.isOverdue ? 'text-red-400' : 'text-blue-400'
          }`}>
            {timeRemaining.days.toString().padStart(2, '0')}
          </div>
          <div className="text-xs text-slate-400">DAYS</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono ${
            timeRemaining.isOverdue ? 'text-red-400' : 'text-blue-400'
          }`}>
            {timeRemaining.hours.toString().padStart(2, '0')}
          </div>
          <div className="text-xs text-slate-400">HRS</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono ${
            timeRemaining.isOverdue ? 'text-red-400' : 'text-blue-400'
          }`}>
            {timeRemaining.minutes.toString().padStart(2, '0')}
          </div>
          <div className="text-xs text-slate-400">MIN</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono ${
            timeRemaining.isOverdue ? 'text-red-400' : 'text-blue-400'
          }`}>
            {timeRemaining.seconds.toString().padStart(2, '0')}
          </div>
          <div className="text-xs text-slate-400">SEC</div>
        </div>
      </div>
    </div>
  );
};

// Task Card Component
const TaskCard = ({ task, onStatusUpdate, onDelete, isAdmin }) => {
  const priorityColors = {
    low: 'bg-green-900/20 text-green-400 border-green-700/30',
    medium: 'bg-yellow-900/20 text-yellow-400 border-yellow-700/30',
    high: 'bg-red-900/20 text-red-400 border-red-700/30'
  };

  const statusColors = {
    pending: 'bg-blue-900/20 text-blue-400 border-blue-700/30',
    completed: 'bg-green-900/20 text-green-400 border-green-700/30',
    overdue: 'bg-red-900/20 text-red-400 border-red-700/30'
  };

  const handleStatusToggle = async () => {
    const newStatus = task.status === 'completed' ? 'pending' : 'completed';
    await onStatusUpdate(task.id, newStatus);
  };

  return (
    <Card className="bg-slate-900/50 border-slate-700/30 hover:bg-slate-900/70 transition-all duration-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <CardTitle className="text-slate-100 text-lg">{task.title}</CardTitle>
            <div className="flex gap-2 flex-wrap">
              <Badge className={`text-xs ${priorityColors[task.priority]}`}>
                {task.priority.toUpperCase()}
              </Badge>
              <Badge className={`text-xs ${statusColors[task.status]}`}>
                {task.status.toUpperCase()}
              </Badge>
              {isAdmin && (
                <Badge className="text-xs bg-purple-900/20 text-purple-400 border-purple-700/30">
                  {task.client_name}
                </Badge>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleStatusToggle}
              className="text-green-400 hover:text-green-300 hover:bg-green-900/20"
            >
              <CheckCircle className="w-4 h-4" />
            </Button>
            {isAdmin && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onDelete(task.id)}
                className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {task.description && (
          <p className="text-slate-300 text-sm leading-relaxed">{task.description}</p>
        )}
        
        <div className="flex items-center gap-4 text-sm text-slate-400 flex-wrap">
          <div className="flex items-center gap-2">
            <CalendarDays className="w-4 h-4" />
            <span>{format(new Date(task.due_datetime), 'PPp')}</span>
          </div>
          {task.project_price && (
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              <span>${task.project_price.toLocaleString()}</span>
            </div>
          )}
        </div>
        
        <CountdownTimer dueDateTime={task.due_datetime} status={task.status} />
      </CardContent>
    </Card>
  );
};

// Task Form Component
const TaskForm = ({ onSubmit, onClose }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    due_date: '',
    due_time: '12:00',
    project_price: '',
    priority: 'medium'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title || !formData.due_date) {
      toast.error('Please fill in required fields');
      return;
    }

    // Combine date and time
    const dueDateTime = new Date(`${formData.due_date}T${formData.due_time}:00`);

    const taskData = {
      title: formData.title,
      description: formData.description,
      due_datetime: dueDateTime.toISOString(),
      project_price: formData.project_price ? parseFloat(formData.project_price) : null,
      priority: formData.priority
    };

    await onSubmit(taskData);
    onClose();
  };

  // Get today's date in YYYY-MM-DD format for min date
  const today = new Date().toISOString().split('T')[0];

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="title" className="text-slate-200">Task Title *</Label>
        <Input
          id="title"
          value={formData.title}
          onChange={(e) => setFormData({...formData, title: e.target.value})}
          className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          placeholder="Enter task title"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description" className="text-slate-200">Description</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({...formData, description: e.target.value})}
          className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          placeholder="Enter task description"
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="due_date" className="text-slate-200">Due Date *</Label>
          <Input
            id="due_date"
            type="date"
            value={formData.due_date}
            min={today}
            onChange={(e) => setFormData({...formData, due_date: e.target.value})}
            className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="due_time" className="text-slate-200">Due Time</Label>
          <Input
            id="due_time"
            type="time"
            value={formData.due_time}
            onChange={(e) => setFormData({...formData, due_time: e.target.value})}
            className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="priority" className="text-slate-200">Priority</Label>
          <Select value={formData.priority} onValueChange={(value) => setFormData({...formData, priority: value})}>
            <SelectTrigger className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-600 text-slate-100">
              <SelectItem value="low" className="text-slate-100 hover:bg-slate-700">Low</SelectItem>
              <SelectItem value="medium" className="text-slate-100 hover:bg-slate-700">Medium</SelectItem>
              <SelectItem value="high" className="text-slate-100 hover:bg-slate-700">High</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="project_price" className="text-slate-200">Project Price ($)</Label>
          <Input
            id="project_price"
            type="number"
            min="0"
            step="0.01"
            value={formData.project_price}
            onChange={(e) => setFormData({...formData, project_price: e.target.value})}
            className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            placeholder="0.00"
          />
        </div>
      </div>

      <div className="flex gap-4 pt-4">
        <Button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white">
          Create Task
        </Button>
        <Button type="button" variant="outline" onClick={onClose} className="border-slate-600 text-slate-200 hover:bg-slate-700">
          Cancel
        </Button>
      </div>
    </form>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const isAdmin = user?.role === 'admin';

  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API}/tasks`, { withCredentials: true });
      setTasks(response.data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      toast.error('Failed to load tasks');
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/tasks/stats/overview`, { withCredentials: true });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const createTask = async (taskData) => {
    try {
      await axios.post(`${API}/tasks`, taskData, { withCredentials: true });
      toast.success('Task created successfully!');
      fetchTasks();
      fetchStats();
    } catch (error) {
      console.error('Error creating task:', error);
      toast.error('Failed to create task');
    }
  };

  const updateTaskStatus = async (taskId, status) => {
    try {
      await axios.put(`${API}/tasks/${taskId}/status?status=${status}`, {}, { withCredentials: true });
      toast.success('Task status updated!');
      fetchTasks();
      fetchStats();
    } catch (error) {
      console.error('Error updating task status:', error);
      toast.error('Failed to update task status');
    }
  };

  const deleteTask = async (taskId) => {
    if (!isAdmin) return;
    
    try {
      await axios.delete(`${API}/tasks/${taskId}`, { withCredentials: true });
      toast.success('Task deleted successfully!');
      fetchTasks();
      fetchStats();
    } catch (error) {
      console.error('Error deleting task:', error);
      toast.error('Failed to delete task');
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchTasks(), fetchStats()]);
      setLoading(false);
    };
    
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-4">
              <img 
                src="https://customer-assets.emergentagent.com/job_taskmaster-pro-11/artifacts/shvxprc6_Rusithink_logo.webp" 
                alt="RusiThink Logo" 
                className="h-12 w-auto"
              />
              <div>
                <h1 className="text-3xl font-bold text-slate-100 mb-2">
                  RusiThink
                  {isAdmin && <Badge className="ml-3 bg-red-900/20 text-red-400 border-red-700/30">ADMIN</Badge>}
                </h1>
                <p className="text-slate-400">
                  {isAdmin ? 'Manage all projects and client tasks' : 'Manage your projects and track deadlines'}
                </p>
              </div>
            </div>
            
            <div className="flex gap-3">
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <Plus className="w-4 h-4 mr-2" />
                    New Task
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-slate-900 border-slate-700 text-slate-100 max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Create New Task</DialogTitle>
                    <DialogDescription className="text-slate-400">
                      Add a new task to your project timeline
                    </DialogDescription>
                  </DialogHeader>
                  <TaskForm onSubmit={createTask} onClose={() => setIsDialogOpen(false)} />
                </DialogContent>
              </Dialog>
              
              <Button onClick={logout} variant="outline" className="border-slate-600 text-slate-200">
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>

        {/* User Info */}
        <div className="bg-slate-900/30 rounded-lg p-4 mb-8">
          <div className="flex items-center gap-3">
            {user?.picture ? (
              <img src={user.picture} alt={user.name} className="w-10 h-10 rounded-full" />
            ) : (
              <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-slate-400" />
              </div>
            )}
            <div>
              <p className="text-slate-100 font-medium">{user?.name}</p>
              <p className="text-slate-400 text-sm">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-900/50 border-slate-700/30">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-900/20 rounded-lg">
                  <Clock className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">{stats.total_tasks || 0}</p>
                  <p className="text-slate-400 text-sm">Total Tasks</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/50 border-slate-700/30">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-yellow-900/20 rounded-lg">
                  <AlertCircle className="w-6 h-6 text-yellow-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">{stats.pending_tasks || 0}</p>
                  <p className="text-slate-400 text-sm">Pending</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/50 border-slate-700/30">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-900/20 rounded-lg">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">{stats.completed_tasks || 0}</p>
                  <p className="text-slate-400 text-sm">Completed</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/50 border-slate-700/30">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-emerald-900/20 rounded-lg">
                  <DollarSign className="w-6 h-6 text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-100">
                    ${(stats.total_project_value || 0).toLocaleString()}
                  </p>
                  <p className="text-slate-400 text-sm">Total Value</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tasks Grid */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-slate-100">
            {isAdmin ? 'All Tasks' : 'Your Tasks'}
          </h2>
          
          {tasks.length === 0 ? (
            <Card className="bg-slate-900/50 border-slate-700/30">
              <CardContent className="p-12 text-center">
                <Clock className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-300 mb-2">No tasks yet</h3>
                <p className="text-slate-500 mb-4">Create your first task to get started</p>
                <Button onClick={() => setIsDialogOpen(true)} className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Task
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {tasks.map(task => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onStatusUpdate={updateTaskStatus}
                  onDelete={deleteTask}
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          )}
        </div>
      </div>
      
      <Toaster 
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            border: '1px solid #334155',
            color: '#f1f5f9'
          }
        }}
      />
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // Handle OAuth callback
  if (location.hash.includes('session_id')) {
    return <OAuthHandler />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;