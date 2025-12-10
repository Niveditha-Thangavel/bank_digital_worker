import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, User, Shield, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

type LoginType = 'customer' | 'admin';

export default function Login() {
  const navigate = useNavigate();
  const { loginCustomer, loginAdmin } = useAuth();
  
  const [loginType, setLoginType] = useState<LoginType>('customer');
  const [customerId, setCustomerId] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      let success = false;
      
      if (loginType === 'customer') {
        if (!customerId.trim()) {
          setError('Please enter your Customer ID');
          return;
        }
        success = loginCustomer(customerId, password);
        if (success) {
          navigate('/chat');
        } else {
          setError('Invalid Customer ID or password. Valid IDs: C101-C110');
        }
      } else {
        if (!email.trim()) {
          setError('Please enter your email');
          return;
        }
        success = loginAdmin(email, password);
        if (success) {
          navigate('/admin/chat');
        } else {
          setError('Invalid email or password');
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary to-primary/80" />
        <div className="relative z-10 flex flex-col justify-center px-16 text-primary-foreground">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-primary-foreground/20 flex items-center justify-center">
              <Building2 className="w-7 h-7" />
            </div>
            <span className="text-2xl font-bold">Banking Agent</span>
          </div>
          <h1 className="text-4xl font-bold mb-4">
            Smart Loan Eligibility<br />Assessment
          </h1>
          <p className="text-primary-foreground/80 text-lg max-w-md">
            Get instant decisions on loan applications with our AI-powered banking agent. 
            Check eligibility, view statements, and understand decisions clearly.
          </p>
          
          <div className="mt-12 space-y-4">
            <div className="flex items-center gap-3 text-primary-foreground/80">
              <div className="w-8 h-8 rounded-full bg-primary-foreground/20 flex items-center justify-center">
                ✓
              </div>
              <span>Instant eligibility checks</span>
            </div>
            <div className="flex items-center gap-3 text-primary-foreground/80">
              <div className="w-8 h-8 rounded-full bg-primary-foreground/20 flex items-center justify-center">
                ✓
              </div>
              <span>Clear decision explanations</span>
            </div>
            <div className="flex items-center gap-3 text-primary-foreground/80">
              <div className="w-8 h-8 rounded-full bg-primary-foreground/20 flex items-center justify-center">
                ✓
              </div>
              <span>Secure and confidential</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <Building2 className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold text-foreground">Banking Agent</span>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-foreground mb-2">Welcome back</h2>
            <p className="text-muted-foreground">Sign in to access your account</p>
          </div>

          {/* Login Type Toggle */}
          <div className="flex rounded-lg bg-muted p-1 mb-6">
            <button
              type="button"
              onClick={() => { setLoginType('customer'); setError(''); }}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium transition-all',
                loginType === 'customer'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <User className="w-4 h-4" />
              Customer
            </button>
            <button
              type="button"
              onClick={() => { setLoginType('admin'); setError(''); }}
              className={cn(
                'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium transition-all',
                loginType === 'admin'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <Shield className="w-4 h-4" />
              Admin
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {loginType === 'customer' ? (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Customer ID
                </label>
                <Input
                  type="text"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value.toUpperCase())}
                  placeholder="e.g., C101"
                  className="uppercase"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Valid IDs: C101, C102, C103... C110
                </p>
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">
                  Email
                </label>
                <Input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@bankagent.com"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Password
              </label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {loginType === 'admin' && (
                <p className="text-xs text-muted-foreground mt-1">
                  Demo: admin@bankagent.com / admin123
                </p>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 text-destructive text-sm bg-destructive/10 p-3 rounded-lg">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
