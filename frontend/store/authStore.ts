import { create } from 'zustand';

interface AuthState {
  token: string | null;
  role: string | null;
  fullName: string | null;
  email: string | null;
  isAuthenticated: boolean;
  login: (token: string, role: string, fullName: string, email: string) => void;
  logout: () => void;
  initialize: () => void;
  updateUser: (fullName: string, email?: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  role: null,
  fullName: null,
  email: null,
  isAuthenticated: false,
  login: (token, role, fullName, email) => {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    localStorage.setItem('fullName', fullName);
    localStorage.setItem('email', email);
    set({ token, role, fullName, email, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('fullName');
    localStorage.removeItem('email');
    set({ token: null, role: null, fullName: null, email: null, isAuthenticated: false });
  },
  initialize: () => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      const role = localStorage.getItem('role');
      const fullName = localStorage.getItem('fullName');
      const email = localStorage.getItem('email');
      if (token && role && fullName && email) {
        set({ token, role, fullName, email, isAuthenticated: true });
      }
    }
  },
  updateUser: (fullName, email) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('fullName', fullName);
      if (email) {
        localStorage.setItem('email', email);
      }
    }
    if (email) {
      set({ fullName, email });
    } else {
      set({ fullName });
    }
  }
}));
