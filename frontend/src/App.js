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
import { CalendarDays, Clock, DollarSign, Plus, CheckCircle, AlertCircle, Timer, Trash2, LogOut, User, Shield, Users, MessageSquare, Bell, Send, Eye, Download, Edit2, Save, X } from "lucide-react";
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
        <div className="flex justify-center mb-4">
          <img 
            src="https://customer-assets.emergentagent.com/job_taskmaster-pro-11/artifacts/shvxprc6_Rusithink_logo.webp" 
            alt="RusiThink Logo" 
            className="h-12 w-auto"
          />
        </div>
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
  const [showRegister, setShowRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [registerData, setRegisterData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    phone: '',
    company_name: ''
  });

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

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);

    if (registerData.password !== registerData.confirmPassword) {
      toast.error('Passwords do not match');
      setLoading(false);
      return;
    }

    if (registerData.password.length < 6) {
      toast.error('Password must be at least 6 characters');
      setLoading(false);
      return;
    }

    try {
      const { confirmPassword, ...registrationData } = registerData;
      const response = await axios.post(`${API}/auth/register`, registrationData, { withCredentials: true });
      await login(response.data.user);
      toast.success(`Welcome ${response.data.user.name}! Registration successful.`);
      navigate('/dashboard');
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed';
      toast.error(message);
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
          <p className="text-slate-400">
            {showRegister ? 'Create your account' : 'Sign in to manage your projects'}
          </p>
        </div>

        <Card className="bg-slate-900/50 border-slate-700/30">
          <CardHeader>
            <CardTitle className="text-slate-100">
              {showRegister ? 'Sign Up for RusiThink' : 'Sign In to RusiThink'}
            </CardTitle>
            <CardDescription className="text-slate-400">
              {showRegister ? 'Fill in your details to get started' : 'Choose your sign-in method'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {!showAdminLogin && !showRegister ? (
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

                <div className="grid grid-cols-2 gap-3">
                  <Button
                    onClick={() => setShowRegister(true)}
                    className="w-full bg-green-600 hover:bg-green-700 text-white"
                    size="lg"
                  >
                    <Plus className="w-5 h-5 mr-2" />
                    Sign Up
                  </Button>
                  
                  <Button
                    onClick={() => setShowAdminLogin(true)}
                    variant="outline"
                    className="w-full border-slate-600 text-slate-200 hover:bg-slate-800"
                    size="lg"
                  >
                    <Shield className="w-5 h-5 mr-2" />
                    Admin
                  </Button>
                </div>
              </>
            ) : showRegister ? (
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name" className="text-slate-200">First Name *</Label>
                    <Input
                      id="first_name"
                      type="text"
                      value={registerData.first_name}
                      onChange={(e) => setRegisterData({...registerData, first_name: e.target.value})}
                      className="bg-slate-800 border-slate-600 text-slate-100"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name" className="text-slate-200">Last Name *</Label>
                    <Input
                      id="last_name"
                      type="text"
                      value={registerData.last_name}
                      onChange={(e) => setRegisterData({...registerData, last_name: e.target.value})}
                      className="bg-slate-800 border-slate-600 text-slate-100"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-200">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={registerData.email}
                    onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone" className="text-slate-200">Phone Number *</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={registerData.phone}
                    onChange={(e) => setRegisterData({...registerData, phone: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="company_name" className="text-slate-200">Company Name *</Label>
                  <Input
                    id="company_name"
                    type="text"
                    value={registerData.company_name}
                    onChange={(e) => setRegisterData({...registerData, company_name: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-200">Password *</Label>
                  <Input
                    id="password"
                    type="password"
                    value={registerData.password}
                    onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                    minLength={6}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword" className="text-slate-200">Confirm Password *</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    value={registerData.confirmPassword}
                    onChange={(e) => setRegisterData({...registerData, confirmPassword: e.target.value})}
                    className="bg-slate-800 border-slate-600 text-slate-100"
                    required
                    minLength={6}
                  />
                </div>
                
                <div className="flex gap-3 pt-4">
                  <Button 
                    type="submit" 
                    disabled={loading}
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                  >
                    {loading ? 'Creating Account...' : 'Create Account'}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => setShowRegister(false)}
                    variant="outline"
                    className="border-slate-600 text-slate-200"
                  >
                    Back
                  </Button>
                </div>
              </form>
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

// Simple Dashboard for now (will be expanded later)
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(false);
  const isAdmin = user?.role === 'admin';

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img 
              src="https://customer-assets.emergentagent.com/job_taskmaster-pro-11/artifacts/shvxprc6_Rusithink_logo.webp" 
              alt="RusiThink Logo" 
              className="h-12 w-auto"
            />
          </div>
          <div className="loading-spinner mx-auto mb-4"></div>
          <div className="text-slate-400">Loading...</div>
        </div>
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
              {user?.company_name && (
                <p className="text-slate-500 text-xs">{user.company_name}</p>
              )}
            </div>
          </div>
        </div>

        {/* Welcome Message */}
        <Card className="bg-slate-900/50 border-slate-700/30">
          <CardContent className="p-12 text-center">
            <h3 className="text-xl font-semibold text-slate-100 mb-4">
              Welcome to RusiThink!
            </h3>
            <p className="text-slate-400 mb-6">
              {isAdmin 
                ? 'User registration system has been successfully implemented. You can now manage all users and their project details.'
                : 'Your account has been created successfully. Full project management features are being finalized.'}
            </p>
            {isAdmin && (
              <Badge className="bg-green-900/20 text-green-400 border-green-700/30">
                ✅ Registration System Active
              </Badge>
            )}
          </CardContent>
        </Card>
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
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img 
              src="https://customer-assets.emergentagent.com/job_taskmaster-pro-11/artifacts/shvxprc6_Rusithink_logo.webp" 
              alt="RusiThink Logo" 
              className="h-12 w-auto"
            />
          </div>
          <div className="loading-spinner"></div>
        </div>
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