import React, { useState, useEffect, useRef } from "react";
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
import { CalendarDays, Clock, DollarSign, Plus, CheckCircle, AlertCircle, Timer, Trash2, LogOut, User, Shield, Users, MessageSquare, Bell, Send, Eye, Download, Edit2, Save, X, Upload, Image as ImageIcon, FileText, Paperclip, Edit, Check } from "lucide-react";
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
    <div className="min-h-screen bg-black flex items-center justify-center">
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
    company_name: '',
    address: ''
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
    <div className="min-h-screen bg-black flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <img 
              src="https://customer-assets.emergentagent.com/job_taskmaster-pro-11/artifacts/shvxprc6_Rusithink_logo.webp" 
              alt="RusiThink Logo" 
              className="h-16 w-auto"
            />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">RusiThink</h2>
          <p className="text-gray-300">
            {showRegister ? 'Create your account' : 'Sign in to manage your projects'}
          </p>
        </div>

        <Card className="bg-gray-900 border-yellow-600/30 shadow-2xl">
          <CardHeader>
            <CardTitle className="text-white">
              {showRegister ? 'Sign Up for RusiThink' : 'Sign In to RusiThink'}
            </CardTitle>
            <CardDescription className="text-gray-400">
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
                    <span className="w-full border-t border-gray-600" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-gray-900 px-2 text-gray-400">Or</span>
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
                    className="w-full border-yellow-500 text-yellow-500 hover:bg-yellow-500 hover:text-black"
                    size="lg"
                  >
                    <Shield className="w-5 h-5 mr-2" />
                    Admin
                  </Button>
                </div>
              </>
            ) : showRegister ? (
              // Registration form
              <form onSubmit={handleRegister} className="space-y-4">
                <h3 className="text-xl font-semibold text-white mb-4">Create Your Account</h3>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name" className="text-gray-200">First Name *</Label>
                    <Input
                      id="first_name"
                      type="text"
                      value={registerData.first_name}
                      onChange={(e) => setRegisterData({...registerData, first_name: e.target.value})}
                      className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="last_name" className="text-gray-200">Last Name *</Label>
                    <Input
                      id="last_name"
                      type="text"
                      value={registerData.last_name}
                      onChange={(e) => setRegisterData({...registerData, last_name: e.target.value})}
                      className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email" className="text-gray-200">Email Address *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={registerData.email}
                    onChange={(e) => setRegisterData({...registerData, email: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone" className="text-gray-200">Phone Number *</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={registerData.phone}
                    onChange={(e) => setRegisterData({...registerData, phone: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="company_name" className="text-gray-200">Company Name *</Label>
                  <Input
                    id="company_name"
                    type="text"
                    value={registerData.company_name}
                    onChange={(e) => setRegisterData({...registerData, company_name: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="address" className="text-gray-200">Address</Label>
                  <Textarea
                    id="address"
                    value={registerData.address}
                    onChange={(e) => setRegisterData({...registerData, address: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    placeholder="Enter your address (optional)"
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-gray-200">Password *</Label>
                  <Input
                    id="password"
                    type="password"
                    value={registerData.password}
                    onChange={(e) => setRegisterData({...registerData, password: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                    minLength={6}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword" className="text-gray-200">Confirm Password *</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    value={registerData.confirmPassword}
                    onChange={(e) => setRegisterData({...registerData, confirmPassword: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                  />
                </div>

                <div className="flex gap-4 pt-4">
                  <Button 
                    type="submit" 
                    disabled={loading}
                    className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-black font-semibold"
                  >
                    {loading ? 'Creating Account...' : 'Create Account'}
                  </Button>
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => setShowRegister(false)}
                    className="border-gray-600 text-gray-200 hover:bg-gray-800"
                  >
                    Back
                  </Button>
                </div>
              </form>
            ) : (
              // Admin login form
              <form onSubmit={handleAdminLogin} className="space-y-4">
                <h3 className="text-xl font-semibold text-white mb-4">Admin Access</h3>
                
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-gray-200">Username</Label>
                  <Input
                    id="username"
                    type="text"
                    value={adminLogin.username}
                    onChange={(e) => setAdminLogin({...adminLogin, username: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="admin-password" className="text-gray-200">Password</Label>
                  <Input
                    id="admin-password"
                    type="password"
                    value={adminLogin.password}
                    onChange={(e) => setAdminLogin({...adminLogin, password: e.target.value})}
                    className="bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
                    required
                  />
                </div>

                <div className="flex gap-4 pt-4">
                  <Button
                    type="submit"
                    disabled={loading}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold"
                  >
                    {loading ? 'Signing in...' : 'Admin Sign In'}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => setShowAdminLogin(false)}
                    variant="outline"
                    className="border-gray-600 text-gray-200 hover:bg-gray-800"
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

// Admin Chat Manager Component
const AdminChatManager = ({ isVisible, onClose }) => {
  const [conversations, setConversations] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/admin/chat/conversations`, { withCredentials: true });
      setConversations(response.data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
      toast.error('Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  const exportClientChat = async (clientId, clientName) => {
    try {
      const response = await axios.get(`${API}/admin/chat/export/${clientId}`, { 
        withCredentials: true,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `chat_export_${clientName}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Chat exported for ${clientName}`);
    } catch (error) {
      console.error('Error exporting chat:', error);
      toast.error('Failed to export chat');
    }
  };

  useEffect(() => {
    if (isVisible) {
      fetchConversations();
      // Refresh conversations every 30 seconds only when dialog is visible
      const interval = setInterval(() => {
        if (isVisible && !document.hidden) {
          fetchConversations();
        }
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <Dialog open={isVisible} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-slate-100 max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <MessageSquare className="w-6 h-6 text-blue-400" />
            Client Chat Management
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            View and manage conversations with all clients
          </DialogDescription>
        </DialogHeader>

        <div className="flex h-[70vh] gap-4">
          {/* Conversations List */}
          <div className="w-1/3 border-r border-slate-700 pr-4">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Client Conversations</h3>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="loading-spinner mx-auto mb-4"></div>
                <p className="text-slate-400">Loading conversations...</p>
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">No conversations yet</p>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-full">
                {conversations.map((conv) => (
                  <Card 
                    key={conv.client_id}
                    className={`cursor-pointer transition-all ${
                      selectedClient?.client_id === conv.client_id
                        ? 'bg-blue-900/20 border-blue-700/30'
                        : 'bg-slate-800/30 border-slate-700/30 hover:bg-slate-800/50'
                    }`}
                    onClick={() => setSelectedClient(conv)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium text-slate-100">{conv.client_name}</h4>
                            {conv.unread_count > 0 && (
                              <Badge className="bg-orange-600 text-white text-xs">
                                {conv.unread_count}
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-slate-400">{conv.client_email}</p>
                          {conv.client_company && (
                            <p className="text-xs text-slate-500">{conv.client_company}</p>
                          )}
                          {conv.last_message && (
                            <p className="text-xs text-slate-400 mt-2 truncate">
                              {conv.last_message}...
                            </p>
                          )}
                          {conv.last_message_time && (
                            <p className="text-xs text-slate-500 mt-1">
                              {format(new Date(conv.last_message_time), 'MMM dd, HH:mm')}
                            </p>
                          )}
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            exportClientChat(conv.client_id, conv.client_name);
                          }}
                          className="text-green-400 hover:text-green-300 hover:bg-green-900/20"
                          title="Export chat history"
                        >
                          <Download className="w-3 h-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Chat Interface */}
          <div className="flex-1">
            {selectedClient ? (
              <div className="h-full">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-100">
                      Chat with {selectedClient.client_name}
                    </h3>
                    <p className="text-sm text-slate-400">{selectedClient.client_email}</p>
                  </div>
                  <Button
                    onClick={() => exportClientChat(selectedClient.client_id, selectedClient.client_name)}
                    className="bg-green-600 hover:bg-green-700 text-white"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export Chat
                  </Button>
                </div>
                
                <ChatSystem 
                  user={{ id: 'admin', name: 'Admin', role: 'admin' }}
                  adminUserId={selectedClient.client_id}
                  key={selectedClient.client_id} // Force re-render when client changes
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400">
                <div className="text-center">
                  <MessageSquare className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                  <p>Select a client to view conversation</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Enhanced Chat System Component with better real-time updates
const ChatSystem = ({ user, adminUserId, taskId = null }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Determine recipient based on user role
  // For clients: recipient should be admin (adminUserId)
  // For admin in chat manager: recipient should be the selected client (adminUserId holds client ID)
  const recipientId = adminUserId;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchMessages = async () => {
    if (!recipientId) return;
    
    // Don't fetch if already loading to prevent multiple simultaneous requests
    if (loading) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (taskId) params.append('task_id', taskId);
      
      const response = await axios.get(`${API}/chat/messages${params.toString() ? `?${params}` : ''}`, { 
        withCredentials: true,
        timeout: 5000 // Add timeout to prevent hanging requests
      });
      
      setMessages(response.data);
    } catch (error) {
      // Only log errors that aren't network timeouts to reduce console spam
      if (error.code !== 'ECONNABORTED') {
        console.error('Error fetching messages:', error);
      }
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !recipientId || loading) return;

    const messageToSend = newMessage.trim();
    setNewMessage(''); // Clear input immediately for better UX
    
    try {
      const messageData = {
        content: messageToSend,
        recipient_id: recipientId,
        task_id: taskId
      };

      await axios.post(`${API}/chat/messages`, messageData, { withCredentials: true });
      // Don't show success toast for every message to avoid spam
      // Fetch messages immediately without waiting for polling
      fetchMessages();
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
      // Restore message if failed
      setNewMessage(messageToSend);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file || !recipientId) return;

    // Validate file size (16MB limit)
    if (file.size > 16 * 1024 * 1024) {
      toast.error('File too large. Maximum size is 16MB');
      event.target.value = '';
      return;
    }

    // Validate file type
    const allowedTypes = ['.png', '.jpg', '.jpeg', '.pdf', '.heic', '.csv'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExtension)) {
      toast.error('File type not allowed. Only PNG, JPG, PDF, HEIC, and CSV files are permitted');
      event.target.value = '';
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('recipient_id', recipientId);
      formData.append('content', `Shared file: ${file.name}`);
      if (taskId) formData.append('task_id', taskId);

      await axios.post(`${API}/chat/upload`, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      fetchMessages(); // Refresh messages immediately
      toast.success('File uploaded successfully');
    } catch (error) {
      console.error('Error uploading file:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to upload file';
      toast.error(errorMsg);
    } finally {
      setUploading(false);
      event.target.value = ''; // Clear file input
    }
  };

  useEffect(() => {
    if (recipientId) {
      fetchMessages();
      
      // Optimized polling with visibility API
      const interval = setInterval(() => {
        // Only fetch if document is visible and component is still mounted
        if (!document.hidden && recipientId && !loading) {
          fetchMessages();
        }
      }, 5000); // 5 second intervals
      
      // Pause/resume polling based on tab visibility
      const handleVisibilityChange = () => {
        if (!document.hidden && recipientId) {
          fetchMessages(); // Fetch immediately when tab becomes active
        }
      };
      
      document.addEventListener('visibilitychange', handleVisibilityChange);
      
      return () => {
        clearInterval(interval);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      };
    }
  }, [recipientId, taskId]);

  useEffect(() => {
    // Only scroll to bottom if not loading to avoid interrupting user interactions
    if (!loading && messages.length > 0) {
      scrollToBottom();
    }
  }, [messages, loading]);

  if (!recipientId) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <div className="text-center">
          <MessageSquare className="w-12 h-12 mx-auto mb-4 text-slate-600" />
          <p>Chat system loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-96 bg-gray-900/50 rounded-lg border border-gray-700/30 overflow-hidden">
      {/* Chat Header */}
      <div className="p-4 border-b border-gray-700/30 flex-shrink-0">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-yellow-400" />
          {taskId ? 'Project Chat' : 'General Chat'}
        </h3>
        <p className="text-sm text-gray-400">
          {user.role === 'admin' ? 'Chat with client' : 'Chat with admin'}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span className="text-xs text-gray-500">Real-time chat</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
        {loading ? (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-yellow-400 mb-2"></div>
            <p className="text-gray-400 text-sm">Loading messages...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">No messages yet. Start the conversation!</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender_id === user.id ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.sender_id === user.id
                    ? 'bg-yellow-600 text-black'
                    : 'bg-gray-800 text-white'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium">
                    {message.sender_name}
                  </span>
                  <Badge className={`text-xs ${
                    message.sender_role === 'admin' 
                      ? 'bg-red-900/20 text-red-400 border-red-700/30'
                      : 'bg-blue-900/20 text-blue-400 border-blue-700/30'
                  }`}>
                    {message.sender_role.toUpperCase()}
                  </Badge>
                </div>
                
                {message.message_type === 'file' && (
                  <div className="mb-2">
                    <a
                      href={`${BACKEND_URL}${message.file_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`flex items-center gap-2 underline ${
                        message.sender_id === user.id ? 'text-black hover:text-gray-800' : 'text-yellow-300 hover:text-yellow-200'
                      }`}
                    >
                      {message.file_name?.toLowerCase().endsWith('.pdf') ? (
                        <FileText className="w-4 h-4" />
                      ) : message.file_name?.toLowerCase().endsWith('.csv') ? (
                        <FileText className="w-4 h-4" />
                      ) : (
                        <ImageIcon className="w-4 h-4" />
                      )}
                      {message.file_name}
                      <span className="text-xs">({(message.file_size / 1024 / 1024).toFixed(1)} MB)</span>
                    </a>
                  </div>
                )}
                
                {message.message_type === 'image' && (
                  <div className="mb-2">
                    <img
                      src={`${BACKEND_URL}${message.file_url}`}
                      alt={message.file_name}
                      className="max-w-full h-auto rounded cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => window.open(`${BACKEND_URL}${message.file_url}`, '_blank')}
                    />
                  </div>
                )}
                
                <p className="text-sm leading-relaxed">{message.content}</p>
                <p className="text-xs opacity-70 mt-1">
                  {format(new Date(message.created_at), 'MMM dd, HH:mm')}
                </p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div className="p-4 border-t border-gray-700/30 flex-shrink-0">
        <div className="flex gap-2">
          <Input
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 bg-gray-800 border-gray-600 text-white focus:border-yellow-500 focus:ring-yellow-500"
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            disabled={loading}
          />
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
            accept=".png,.jpg,.jpeg,.pdf,.heic,.csv"
          />
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || loading}
            variant="outline"
            size="sm"
            className="border-gray-600 text-gray-200 hover:bg-gray-800"
            title="Upload file (PNG, JPG, PDF, HEIC, CSV - Max 16MB)"
          >
            {uploading ? <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400" /> : <Paperclip className="w-4 h-4" />}
          </Button>
          <Button
            onClick={sendMessage}
            disabled={!newMessage.trim() || loading}
            className="bg-yellow-600 hover:bg-yellow-700 text-black font-semibold"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Supported files: PNG, JPG, PDF, HEIC, CSV (Max 16MB)
        </p>
      </div>
    </div>
  );
};

// Project Timeline Component
const ProjectTimeline = ({ task, user }) => {
  const [milestones, setMilestones] = useState([]);
  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTimelineData = async () => {
    setLoading(true);
    try {
      // Fetch milestones and updates
      const [milestonesRes, updatesRes] = await Promise.all([
        axios.get(`${API}/tasks/${task.id}/milestones`, { withCredentials: true }),
        axios.get(`${API}/tasks/${task.id}/updates`, { withCredentials: true })
      ]);
      
      setMilestones(milestonesRes.data);
      setUpdates(updatesRes.data);
    } catch (error) {
      console.error('Error fetching timeline data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (task?.id) {
      fetchTimelineData();
    }
  }, [task?.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner mx-auto mb-4"></div>
        <p className="text-slate-400">Loading timeline...</p>
      </div>
    );
  }

  // Combine milestones and updates into a single timeline
  const timelineItems = [
    ...milestones.map(m => ({ ...m, type: 'milestone' })),
    ...updates.map(u => ({ ...u, type: 'update' }))
  ].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-6">
        <Clock className="w-5 h-5 text-blue-400" />
        <h3 className="text-lg font-semibold text-slate-100">Project Timeline</h3>
      </div>

      {timelineItems.length === 0 ? (
        <div className="text-center py-8">
          <Clock className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">No timeline events yet</p>
        </div>
      ) : (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-slate-700"></div>
          
          <div className="space-y-6">
            {timelineItems.map((item, index) => (
              <div key={`${item.type}-${item.id}`} className="relative flex items-start gap-4">
                {/* Timeline dot */}
                <div className={`relative z-10 w-3 h-3 rounded-full border-2 ${
                  item.type === 'milestone' 
                    ? (item.status === 'completed' ? 'bg-green-500 border-green-500' : 'bg-blue-500 border-blue-500')
                    : 'bg-purple-500 border-purple-500'
                }`}></div>
                
                {/* Timeline content */}
                <div className="flex-1 pb-6">
                  <Card className="bg-slate-800/50 border-slate-700/30">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h4 className="font-medium text-slate-100">
                            {item.type === 'milestone' ? item.title : 'Project Update'}
                          </h4>
                          <p className="text-sm text-slate-400">
                            {format(new Date(item.created_at), 'MMM dd, yyyy HH:mm')}
                          </p>
                        </div>
                        <Badge className={`text-xs ${
                          item.type === 'milestone'
                            ? (item.status === 'completed' 
                                ? 'bg-green-900/20 text-green-400 border-green-700/30'
                                : item.status === 'in_progress'
                                ? 'bg-yellow-900/20 text-yellow-400 border-yellow-700/30'
                                : 'bg-blue-900/20 text-blue-400 border-blue-700/30')
                            : 'bg-purple-900/20 text-purple-400 border-purple-700/30'
                        }`}>
                          {item.type === 'milestone' ? item.status.toUpperCase() : 'UPDATE'}
                        </Badge>
                      </div>
                      
                      <p className="text-slate-300 text-sm leading-relaxed">
                        {item.type === 'milestone' ? item.description : item.content}
                      </p>
                      
                      {item.type === 'milestone' && item.due_date && (
                        <p className="text-xs text-slate-500 mt-2">
                          Due: {format(new Date(item.due_date), 'MMM dd, yyyy')}
                        </p>
                      )}
                      
                      {item.type === 'update' && item.created_by_name && (
                        <p className="text-xs text-slate-500 mt-2">
                          by {item.created_by_name}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Continue with the rest of the components (CountdownTimer, TaskCard, etc.) - same as before
// I'll include them for completeness but they remain largely unchanged

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

// Project Updates Dialog Component  
const ProjectUpdatesDialog = ({ task, isAdmin, open, onClose }) => {
  const [updates, setUpdates] = useState([]);
  const [newUpdate, setNewUpdate] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchUpdates = async () => {
    if (!open || !task) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`${API}/tasks/${task.id}/updates`, { withCredentials: true });
      setUpdates(response.data);
    } catch (error) {
      console.error('Error fetching updates:', error);
      toast.error('Failed to load project updates');
    } finally {
      setLoading(false);
    }
  };

  const addUpdate = async () => {
    if (!newUpdate.trim()) return;
    
    setSubmitting(true);
    try {
      await axios.post(`${API}/tasks/${task.id}/updates`, 
        { content: newUpdate }, 
        { withCredentials: true }
      );
      
      setNewUpdate('');
      toast.success('Project update added successfully!');
      fetchUpdates(); // Refresh updates
    } catch (error) {
      console.error('Error adding update:', error);
      toast.error('Failed to add project update');
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    fetchUpdates();
  }, [open, task]);

  if (!task) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-slate-100 max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader className="sticky top-0 bg-slate-900 pb-4 border-b border-slate-700">
          <DialogTitle className="flex items-center gap-3">
            <MessageSquare className="w-5 h-5 text-blue-400" />
            Project Updates - {task.title}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            {isAdmin ? 'Add progress updates for this project' : 'View project progress updates'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* Add Update Form (Admin Only) */}
          {isAdmin && (
            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
              <Label className="text-slate-200 mb-2 block">Add Progress Update</Label>
              <div className="space-y-3">
                <Textarea
                  value={newUpdate}
                  onChange={(e) => setNewUpdate(e.target.value)}
                  placeholder="Enter project progress update..."
                  className="bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-500 min-h-[100px]"
                  rows={4}
                />
                <Button 
                  onClick={addUpdate}
                  disabled={submitting || !newUpdate.trim()}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {submitting ? 'Adding Update...' : 'Add Update'}
                </Button>
              </div>
            </div>
          )}

          {/* Updates List */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <Clock className="w-5 h-5 text-slate-400" />
              Progress Updates ({updates.length})
            </h3>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="loading-spinner mx-auto mb-4"></div>
                <p className="text-slate-400">Loading updates...</p>
              </div>
            ) : updates.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-300 mb-2">No updates yet</h3>
                <p className="text-slate-500">
                  {isAdmin ? 'Add the first progress update for this project' : 'No progress updates have been added yet'}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {updates.map((update) => (
                  <Card key={update.id} className="bg-slate-800/30 border-slate-700/30">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Badge className="bg-red-900/20 text-red-400 border-red-700/30">
                            ADMIN UPDATE
                          </Badge>
                          <span className="text-sm text-slate-400">
                            by {update.created_by_name}
                          </span>
                        </div>
                        <span className="text-sm text-slate-400">
                          {format(new Date(update.created_at), 'PPp')}
                        </span>
                      </div>
                      <p className="text-slate-200 leading-relaxed whitespace-pre-wrap">
                        {update.content}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Task Card Component
const TaskCard = ({ task, onStatusUpdate, onDelete, isAdmin }) => {
  const [updatesDialogOpen, setUpdatesDialogOpen] = useState(false);
  
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
    <>
      <Card className="bg-gray-900/50 border-gray-700/30 hover:bg-gray-900/70 transition-all duration-200">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <CardTitle className="text-white text-lg flex items-center gap-2">
                {task.title}
                {task.unread_updates > 0 && (
                  <Badge className="bg-yellow-900/20 text-yellow-400 border-yellow-700/30 text-xs">
                    {task.unread_updates} New Update{task.unread_updates > 1 ? 's' : ''}
                  </Badge>
                )}
              </CardTitle>
              <div className="flex gap-2 flex-wrap">
                <Badge className={`text-xs ${priorityColors[task.priority]}`}>
                  {task.priority.toUpperCase()}
                </Badge>
                <Badge className={`text-xs ${statusColors[task.status]}`}>
                  {task.status.toUpperCase()}
                </Badge>
                {isAdmin && task.client_name && (
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
                onClick={() => setUpdatesDialogOpen(true)}
                className="text-yellow-400 hover:text-yellow-300 hover:bg-yellow-900/20"
                title={isAdmin ? "Add project update" : "View project updates"}
              >
                <MessageSquare className="w-4 h-4" />
              </Button>
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
            <p className="text-gray-300 text-sm leading-relaxed">{task.description}</p>
          )}
          
          <div className="flex items-center gap-4 text-sm text-gray-400 flex-wrap">
            <div className="flex items-center gap-2">
              <CalendarDays className="w-4 h-4" />
              <span>{format(new Date(task.due_datetime), 'PPp')}</span>
            </div>
            {task.project_price && (
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-yellow-400" />
                <span className="text-yellow-400 font-semibold">${task.project_price.toLocaleString()}</span>
              </div>
            )}
          </div>
          
          <CountdownTimer dueDateTime={task.due_datetime} status={task.status} />
        </CardContent>
      </Card>
      
      <ProjectUpdatesDialog 
        task={task}
        isAdmin={isAdmin}
        open={updatesDialogOpen}
        onClose={() => setUpdatesDialogOpen(false)}
      />
    </>
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

// Admin User Management Component
const AdminUserManagement = ({ isVisible, onClose }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({});

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/admin/users`, { withCredentials: true });
      setUsers(response.data);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const updateUser = async (userId, userData) => {
    try {
      await axios.put(`${API}/admin/users/${userId}`, userData, { withCredentials: true });
      toast.success('User updated successfully!');
      setEditingUser(null);
      setEditForm({});
      fetchUsers();
    } catch (error) {
      console.error('Error updating user:', error);
      toast.error('Failed to update user');
    }
  };

  const exportCSV = async () => {
    try {
      const response = await axios.get(`${API}/admin/users/export/csv`, { 
        withCredentials: true,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'users_export.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('CSV export downloaded successfully!');
    } catch (error) {
      console.error('Error exporting CSV:', error);
      toast.error('Failed to export CSV');
    }
  };

  const exportPDF = async () => {
    try {
      const response = await axios.get(`${API}/admin/users/export/pdf`, { 
        withCredentials: true,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'users_export.pdf';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF export downloaded successfully!');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      toast.error('Failed to export PDF');
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user.id);
    setEditForm({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      phone: user.phone || '',
      company_name: user.company_name || '',
      address: user.address || '',
      email: user.email
    });
  };

  const handleSave = () => {
    if (editingUser) {
      updateUser(editingUser, editForm);
    }
  };

  const handleCancel = () => {
    setEditingUser(null);
    setEditForm({});
  };

  useEffect(() => {
    if (isVisible) {
      fetchUsers();
    }
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <Dialog open={isVisible} onOpenChange={onClose}>
      <DialogContent className="bg-slate-900 border-slate-700 text-slate-100 max-w-7xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <Users className="w-6 h-6 text-blue-400" />
            User Management
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            Manage registered users and export user data
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Export Buttons */}
          <div className="flex gap-3">
            <Button 
              onClick={exportCSV}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
            <Button 
              onClick={exportPDF}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Export PDF
            </Button>
          </div>

          {/* Users Table */}
          {loading ? (
            <div className="text-center py-8">
              <div className="loading-spinner mx-auto mb-4"></div>
              <p className="text-slate-400">Loading users...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left p-3 text-slate-200">Name</th>
                    <th className="text-left p-3 text-slate-200">Email</th>
                    <th className="text-left p-3 text-slate-200">Phone</th>
                    <th className="text-left p-3 text-slate-200">Company</th>
                    <th className="text-left p-3 text-slate-200">Address</th>
                    <th className="text-left p-3 text-slate-200">Role</th>
                    <th className="text-left p-3 text-slate-200">Type</th>
                    <th className="text-left p-3 text-slate-200">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-b border-slate-800">
                      <td className="p-3">
                        {editingUser === user.id ? (
                          <div className="space-y-1">
                            <Input
                              value={editForm.first_name}
                              onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                              placeholder="First name"
                              className="bg-slate-800 border-slate-600 text-slate-100 text-xs"
                            />
                            <Input
                              value={editForm.last_name}
                              onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                              placeholder="Last name"
                              className="bg-slate-800 border-slate-600 text-slate-100 text-xs"
                            />
                          </div>
                        ) : (
                          <div>
                            <div className="text-slate-100">{user.name}</div>
                            <div className="text-slate-400 text-xs">
                              {user.first_name} {user.last_name}
                            </div>
                          </div>
                        )}
                      </td>
                      <td className="p-3">
                        {editingUser === user.id ? (
                          <Input
                            value={editForm.email}
                            onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                            placeholder="Email"
                            className="bg-slate-800 border-slate-600 text-slate-100 text-xs"
                          />
                        ) : (
                          <div className="text-slate-300">{user.email}</div>
                        )}
                      </td>
                      <td className="p-3">
                        {editingUser === user.id ? (
                          <Input
                            value={editForm.phone}
                            onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                            placeholder="Phone"
                            className="bg-slate-800 border-slate-600 text-slate-100 text-xs"
                          />
                        ) : (
                          <div className="text-slate-300">{user.phone || 'N/A'}</div>
                        )}
                      </td>
                      <td className="p-3">
                        {editingUser === user.id ? (
                          <Input
                            value={editForm.company_name}
                            onChange={(e) => setEditForm({...editForm, company_name: e.target.value})}
                            placeholder="Company"
                            className="bg-slate-800 border-slate-600 text-slate-100 text-xs"
                          />
                        ) : (
                          <div className="text-slate-300">{user.company_name || 'N/A'}</div>
                        )}
                      </td>
                      <td className="p-3">
                        {editingUser === user.id ? (
                          <Textarea
                            value={editForm.address}
                            onChange={(e) => setEditForm({...editForm, address: e.target.value})}
                            placeholder="Address"
                            className="bg-slate-800 border-slate-600 text-slate-100 text-xs"
                            rows={2}
                          />
                        ) : (
                          <div className="text-slate-300 max-w-xs truncate" title={user.address}>
                            {user.address || 'N/A'}
                          </div>
                        )}
                      </td>
                      <td className="p-3">
                        <Badge className={`text-xs ${
                          user.role === 'admin' 
                            ? 'bg-red-900/20 text-red-400 border-red-700/30'
                            : 'bg-blue-900/20 text-blue-400 border-blue-700/30'
                        }`}>
                          {user.role.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3">
                        <Badge className={`text-xs ${
                          user.registration_type === 'oauth'
                            ? 'bg-green-900/20 text-green-400 border-green-700/30'
                            : user.registration_type === 'manual'
                            ? 'bg-yellow-900/20 text-yellow-400 border-yellow-700/30'
                            : 'bg-purple-900/20 text-purple-400 border-purple-700/30'
                        }`}>
                          {user.registration_type?.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3">
                        {editingUser === user.id ? (
                          <div className="flex gap-1">
                            <Button size="sm" onClick={handleSave} className="bg-green-600 hover:bg-green-700 text-white">
                              <Check className="w-3 h-3" />
                            </Button>
                            <Button size="sm" onClick={handleCancel} variant="outline" className="border-slate-600">
                              <X className="w-3 h-3" />
                            </Button>
                          </div>
                        ) : (
                          <Button 
                            size="sm" 
                            onClick={() => handleEdit(user)}
                            variant="ghost"
                            className="text-blue-400 hover:text-blue-300 hover:bg-blue-900/20"
                          >
                            <Edit className="w-3 h-3" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              
              {users.length === 0 && (
                <div className="text-center py-8">
                  <Users className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-300 mb-2">No users found</h3>
                  <p className="text-slate-500">No registered users yet.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Main Dashboard Component
const Dashboard = () => {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [adminUser, setAdminUser] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [showUserManagement, setShowUserManagement] = useState(false);
  const [showChatManagement, setShowChatManagement] = useState(false);

  const isAdmin = user?.role === 'admin';
  const isClient = user?.role === 'client';

  const fetchAdminUser = async () => {
    if (isClient) {
      try {
        // Get admin user info for chat
        const response = await axios.get(`${API}/chat/admin-info`, { withCredentials: true });
        setAdminUser(response.data);
      } catch (error) {
        console.error('Error fetching admin user:', error);
      }
    }
  };

  const fetchUnreadCount = async () => {
    try {
      const response = await axios.get(`${API}/notifications/unread-count`, { withCredentials: true });
      setUnreadCount(response.data.unread_count || 0);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  };

  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API}/tasks`, { withCredentials: true });
      setTasks(response.data);
      
      // Set first task as selected for timeline (client only)
      if (isClient && response.data.length > 0 && !selectedTask) {
        setSelectedTask(response.data[0]);
      }
      
      fetchUnreadCount();
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
      await Promise.all([fetchTasks(), fetchStats(), fetchAdminUser()]);
      setLoading(false);
    };
    
    loadData();
    
    // Polling for updates
    const interval = setInterval(() => {
      fetchUnreadCount();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [isClient]);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
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
    <div className="min-h-screen bg-black">
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
                <h1 className="text-3xl font-bold text-white mb-2">
                  RusiThink
                  {isAdmin && <Badge className="ml-3 bg-red-900/50 text-red-400 border-red-700/30">ADMIN</Badge>}
                </h1>
                <p className="text-gray-300">
                  {isAdmin ? 'Manage all projects and client tasks' : 'Manage your projects and track deadlines'}
                </p>
              </div>
            </div>
            
            <div className="flex gap-3">
              {/* Admin User Management Button */}
              {isAdmin && (
                <Button 
                  onClick={() => setShowUserManagement(true)}
                  variant="outline" 
                  className="border-yellow-500 text-yellow-500 hover:bg-yellow-500 hover:text-black"
                >
                  <Users className="w-4 h-4 mr-2" />
                  Manage Users
                </Button>
              )}
              
              {/* Admin Chat Management Button */}
              {isAdmin && (
                <Button 
                  onClick={() => setShowChatManagement(true)}
                  variant="outline" 
                  className="border-yellow-500 text-yellow-500 hover:bg-yellow-500 hover:text-black"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Chat Center
                </Button>
              )}
              
              {/* Notification Bell */}
              {unreadCount > 0 && (
                <div className="relative">
                  <Bell className="w-6 h-6 text-yellow-400" />
                  <Badge className="absolute -top-2 -right-2 bg-yellow-600 text-black text-xs min-w-[20px] h-5 rounded-full flex items-center justify-center font-semibold">
                    {unreadCount}
                  </Badge>
                </div>
              )}
              
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-yellow-600 hover:bg-yellow-700 text-black font-semibold">
                    <Plus className="w-4 h-4 mr-2" />
                    New Task
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Create New Task</DialogTitle>
                    <DialogDescription className="text-gray-400">
                      Add a new task to your project timeline
                    </DialogDescription>
                  </DialogHeader>
                  <TaskForm onSubmit={createTask} onClose={() => setIsDialogOpen(false)} />
                </DialogContent>
              </Dialog>
              
              <Button onClick={logout} variant="outline" className="border-gray-600 text-gray-200 hover:bg-gray-800">
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>

        {/* User Info */}
        <div className="bg-gray-900/50 rounded-lg p-4 mb-8 border border-gray-700/30">
          <div className="flex items-center gap-3">
            {user?.picture ? (
              <img src={user.picture} alt={user.name} className="w-10 h-10 rounded-full" />
            ) : (
              <div className="w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-gray-400" />
              </div>
            )}
            <div>
              <p className="text-white font-medium">{user?.name}</p>
              <p className="text-gray-400 text-sm">{user?.email}</p>
              {user?.company_name && (
                <p className="text-gray-500 text-xs">{user.company_name}</p>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content Area */}
          <div className="lg:col-span-2 space-y-8">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="bg-gray-900/50 border-gray-700/30">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-yellow-900/20 rounded-lg">
                      <Clock className="w-6 h-6 text-yellow-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">{stats.total_tasks || 0}</p>
                      <p className="text-gray-400 text-sm">Total Tasks</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gray-900/50 border-gray-700/30">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-900/20 rounded-lg">
                      <AlertCircle className="w-6 h-6 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">{stats.pending_tasks || 0}</p>
                      <p className="text-gray-400 text-sm">Pending</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gray-900/50 border-gray-700/30">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-green-900/20 rounded-lg">
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">{stats.completed_tasks || 0}</p>
                      <p className="text-gray-400 text-sm">Completed</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-gray-900/50 border-gray-700/30">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-yellow-900/20 rounded-lg">
                      <DollarSign className="w-6 h-6 text-yellow-400" />
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-white">
                        ${(stats.total_project_value || 0).toLocaleString()}
                      </p>
                      <p className="text-gray-400 text-sm">Total Value</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Tasks Grid */}
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white">
                {isAdmin ? 'All Tasks' : 'Your Tasks'}
              </h2>
              
              {tasks.length === 0 ? (
                <Card className="bg-gray-900/50 border-gray-700/30">
                  <CardContent className="p-12 text-center">
                    <Clock className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-300 mb-2">No tasks yet</h3>
                    <p className="text-gray-500 mb-4">Create your first task to get started</p>
                    <Button onClick={() => setIsDialogOpen(true)} className="bg-yellow-600 hover:bg-yellow-700 text-black font-semibold">
                      <Plus className="w-4 h-4 mr-2" />
                      Create Task
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid grid-cols-1 gap-6">
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

          {/* Right Sidebar - Timeline & Chat for Clients */}
          {isClient && (
            <div className="space-y-6">
              {/* Project Timeline */}
              {selectedTask && (
                <Card className="bg-gray-900/50 border-gray-700/30">
                  <CardContent className="p-6">
                    <ProjectTimeline task={selectedTask} user={user} />
                  </CardContent>
                </Card>
              )}

              {/* Chat System */}
              {adminUser && (
                <Card className="bg-gray-900/50 border-gray-700/30">
                  <CardContent className="p-6">
                    <ChatSystem 
                      user={user} 
                      adminUserId={adminUser.id}
                      taskId={selectedTask?.id}
                    />
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Admin User Management Dialog */}
      {isAdmin && (
        <AdminUserManagement 
          isVisible={showUserManagement}
          onClose={() => setShowUserManagement(false)}
        />
      )}
      
      {/* Admin Chat Management Dialog */}
      {isAdmin && (
        <AdminChatManager 
          isVisible={showChatManagement}
          onClose={() => setShowChatManagement(false)}
        />
      )}
      
      <Toaster 
        theme="dark"
        position="top-right"
        toastOptions={{
          style: {
            background: '#1f2937',
            border: '1px solid #374151',
            color: '#f9fafb'
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
      <div className="min-h-screen bg-black flex items-center justify-center">
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