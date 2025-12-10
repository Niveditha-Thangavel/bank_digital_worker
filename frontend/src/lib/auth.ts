export type UserRole = 'customer' | 'admin';

export interface User {
  id: string;
  role: UserRole;
  name: string;
  email?: string;
  customerId?: string;
}

// Valid customer IDs
const VALID_CUSTOMER_IDS = ['C101', 'C102', 'C103', 'C104', 'C105', 'C106', 'C107', 'C108', 'C109', 'C110'];

// Admin credentials (in production, this would be server-side)
const ADMIN_CREDENTIALS = {
  email: 'admin@bankagent.com',
  password: 'admin123'
};

export function validateCustomerLogin(customerId: string, password: string): User | null {
  const upperCustomerId = customerId.toUpperCase();
  if (VALID_CUSTOMER_IDS.includes(upperCustomerId) && password.length >= 4) {
    return {
      id: upperCustomerId,
      role: 'customer',
      name: `Customer ${upperCustomerId}`,
      customerId: upperCustomerId
    };
  }
  return null;
}

export function validateAdminLogin(email: string, password: string): User | null {
  if (email === ADMIN_CREDENTIALS.email && password === ADMIN_CREDENTIALS.password) {
    return {
      id: 'admin-1',
      role: 'admin',
      name: 'Administrator',
      email: email
    };
  }
  return null;
}

export function getStoredUser(): User | null {
  const stored = localStorage.getItem('bankagent_user');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  }
  return null;
}

export function storeUser(user: User): void {
  localStorage.setItem('bankagent_user', JSON.stringify(user));
}

export function clearStoredUser(): void {
  localStorage.removeItem('bankagent_user');
}
