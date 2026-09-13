import React, { useState } from 'react';
import { Shield, Lock, Eye, EyeOff, User, Mail, CheckCircle2, AlertCircle, Hash, Loader2 } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { authService, User as UserType } from '@/lib/authService';

interface AuthPageProps {
  onLogin: (user: UserType) => void;
}

const AuthPage: React.FC<AuthPageProps> = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [hashingPhase, setHashingPhase] = useState<'idle' | 'hashing' | 'complete'>('idle');
  const [hashedPassword, setHashedPassword] = useState('');

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }

    if (!isLogin) {
      if (!formData.email.trim()) {
        newErrors.email = 'Email is required';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
        newErrors.email = 'Please enter a valid email';
      }
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    if (!isLogin && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Simulate SHA-256 hashing
  const simulatePasswordHash = async (password: string) => {
    setHashingPhase('hashing');
    
    // Simulate hashing delay
    await new Promise(resolve => setTimeout(resolve, 1200));
    
    // Generate a mock SHA-256 hash
    const chars = '0123456789abcdef';
    const hash = Array.from({ length: 64 }, () => 
      chars[Math.floor(Math.random() * chars.length)]
    ).join('');
    
    setHashedPassword(hash);
    setHashingPhase('complete');
    
    await new Promise(resolve => setTimeout(resolve, 800));
    
    return hash;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});
    
    try {
      // Simulate password hashing visualization
      await simulatePasswordHash(formData.password);
      
      if (isLogin) {
        // Real login API call
        const response = await authService.login({
          username: formData.username,
          password: formData.password,
        });
        onLogin(response.user);
      } else {
        // Real registration API call
        await authService.register({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          password_confirm: formData.confirmPassword,
        });
        
        // Auto-login after registration
        const response = await authService.login({
          username: formData.username,
          password: formData.password,
        });
        onLogin(response.user);
      }
    } catch (error: any) {
      const errorMessage = error?.message || 'Authentication failed. Please try again.';
      setErrors({ form: errorMessage });
      if (error?.errors) {
        setErrors(prev => ({ ...prev, ...Object.fromEntries(
          Object.entries(error.errors).map(([key, val]) => [key, (val as string[])[0]])
        )}));
      }
    } finally {
      setIsLoading(false);
      setHashingPhase('idle');
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <TooltipProvider>
      <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-cyber-grid bg-grid opacity-30" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-3xl" />
        
        <div className="w-full max-w-md relative z-10">
          {/* Logo and title */}
          <div className="text-center mb-8 animate-fade-in-up">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-cyber mb-4 animate-shield">
              <Shield className="w-10 h-10 text-primary-foreground" />
            </div>
            <h1 className="text-3xl font-bold text-gradient mb-2">SecureShare</h1>
            <p className="text-muted-foreground">End-to-End Encrypted P2P File Sharing</p>
          </div>

          {/* Auth card */}
          <div className="glass-card cyber-border animated-border p-8">
            {/* Toggle buttons */}
            <div className="flex mb-8 bg-muted rounded-lg p-1">
              <button
                type="button"
                onClick={() => setIsLogin(true)}
                className={`flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-all duration-300 ${
                  isLogin 
                    ? 'bg-gradient-cyber text-primary-foreground glow-primary' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => setIsLogin(false)}
                className={`flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-all duration-300 ${
                  !isLogin 
                    ? 'bg-gradient-cyber text-primary-foreground glow-primary' 
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Register
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Username field */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground flex items-center gap-2">
                  <User className="w-4 h-4 text-primary" />
                  Username
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => handleInputChange('username', e.target.value)}
                    className={`w-full px-4 py-3 cyber-input ${errors.username ? 'border-destructive' : ''}`}
                    placeholder="Enter your username"
                  />
                  {formData.username && !errors.username && (
                    <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-success" />
                  )}
                </div>
                {errors.username && (
                  <p className="text-sm text-destructive flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {errors.username}
                  </p>
                )}
              </div>

              {/* Email field (register only) */}
              {!isLogin && (
                <div className="space-y-2 animate-fade-in-up">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Mail className="w-4 h-4 text-primary" />
                    Email
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      className={`w-full px-4 py-3 cyber-input ${errors.email ? 'border-destructive' : ''}`}
                      placeholder="Enter your email"
                    />
                    {formData.email && !errors.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) && (
                      <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-success" />
                    )}
                  </div>
                  {errors.email && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      {errors.email}
                    </p>
                  )}
                </div>
              )}

              {/* Password field */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground flex items-center gap-2">
                  <Lock className="w-4 h-4 text-primary" />
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    className={`w-full px-4 py-3 pr-12 cyber-input ${errors.password ? 'border-destructive' : ''}`}
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-sm text-destructive flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" />
                    {errors.password}
                  </p>
                )}
              </div>

              {/* Confirm password (register only) */}
              {!isLogin && (
                <div className="space-y-2 animate-fade-in-up">
                  <label className="text-sm font-medium text-foreground flex items-center gap-2">
                    <Lock className="w-4 h-4 text-primary" />
                    Confirm Password
                  </label>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    className={`w-full px-4 py-3 cyber-input ${errors.confirmPassword ? 'border-destructive' : ''}`}
                    placeholder="Confirm your password"
                  />
                  {errors.confirmPassword && (
                    <p className="text-sm text-destructive flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" />
                      {errors.confirmPassword}
                    </p>
                  )}
                </div>
              )}

              {/* Form-level error */}
              {errors.form && (
                <div className="p-4 rounded-xl bg-destructive/10 border border-destructive animate-fade-in-up">
                  <p className="text-sm text-destructive flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {errors.form}
                  </p>
                </div>
              )}

              {/* Password hashing simulation */}
              {hashingPhase !== 'idle' && (
                <div className="p-4 rounded-xl bg-muted/50 border border-border animate-fade-in-up">
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`p-2 rounded-lg ${hashingPhase === 'complete' ? 'bg-success/20' : 'bg-primary/20'}`}>
                      {hashingPhase === 'hashing' ? (
                        <Hash className="w-5 h-5 text-primary animate-spin" />
                      ) : (
                        <CheckCircle2 className="w-5 h-5 text-success" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {hashingPhase === 'hashing' ? 'Hashing password locally...' : 'Password hashed securely'}
                      </p>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-muted-foreground cursor-help">
                            SHA-256 Simulation • Password never leaves your device
                          </p>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p className="text-xs">
                            SHA-256 is a cryptographic hash function that converts your password 
                            into a fixed-size 256-bit (32-byte) hash. This hash is one-way, 
                            meaning the original password cannot be recovered from it.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </div>
                  </div>
                  
                  {hashedPassword && (
                    <div className="mt-2 p-2 rounded bg-background/50">
                      <p className="text-[10px] text-muted-foreground mb-1">SHA-256 Hash:</p>
                      <p className="font-mono text-[10px] text-primary break-all">
                        {hashedPassword}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Submit button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3.5 cyber-btn text-primary-foreground font-semibold rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Authenticating...</span>
                  </>
                ) : (
                  <>
                    <Shield className="w-5 h-5" />
                    <span>{isLogin ? 'Sign In Securely' : 'Create Secure Account'}</span>
                  </>
                )}
              </button>
            </form>

            {/* Security badges */}
            <div className="mt-6 pt-6 border-t border-border">
              <div className="flex items-center justify-center gap-4 text-muted-foreground text-xs">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1 cursor-help">
                      <Lock className="w-3 h-3 text-success" />
                      <span>256-bit Encryption</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">AES-256: Military-grade encryption standard</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1 cursor-help">
                      <Shield className="w-3 h-3 text-success" />
                      <span>Zero-Knowledge</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs">Your data is encrypted before leaving your device</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>

          {/* Bottom note */}
          <p className="text-center text-xs text-muted-foreground mt-6">
            🔒 All cryptographic operations are simulated for demonstration purposes
          </p>
        </div>
      </div>
    </TooltipProvider>
  );
};

export default AuthPage;
