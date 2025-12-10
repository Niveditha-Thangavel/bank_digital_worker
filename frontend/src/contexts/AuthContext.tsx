import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, getStoredUser, storeUser, clearStoredUser, validateCustomerLogin, validateAdminLogin } from '@/lib/auth';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  loginCustomer: (customerId: string, password: string) => boolean;
  loginAdmin: (email: string, password: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
    }
    setIsLoading(false);
  }, []);

  const loginCustomer = (customerId: string, password: string): boolean => {
    const validUser = validateCustomerLogin(customerId, password);
    if (validUser) {
      storeUser(validUser);
      setUser(validUser);
      return true;
    }
    return false;
  };

  const loginAdmin = (email: string, password: string): boolean => {
    const validUser = validateAdminLogin(email, password);
    if (validUser) {
      storeUser(validUser);
      setUser(validUser);
      return true;
    }
    return false;
  };

  const logout = () => {
    clearStoredUser();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, loginCustomer, loginAdmin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
