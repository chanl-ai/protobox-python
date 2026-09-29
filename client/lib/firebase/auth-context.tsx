"use client"

import { createContext, useContext, useEffect, useState } from 'react';
import { 
  User,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  FacebookAuthProvider,
  OAuthProvider,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  sendEmailVerification
} from 'firebase/auth';
import { auth } from './config';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { tokenManager } from '@/lib/auth/token-manager';
import { userStorage } from '@/lib/auth/utils/user-storage';

type AuthContextType = {
  user: User | null;
  customToken: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string) => Promise<{ error: Error | null }>;
  signInWithGoogle: () => Promise<{ error: Error | null }>;
  signInWithApple: () => Promise<{ error: Error | null }>;
  signInWithFacebook: () => Promise<{ error: Error | null }>;
  logout: () => Promise<void>;
  signOut: () => Promise<void>; // Alias for logout for compatibility
  resetPassword: (email: string) => Promise<{ error: Error | null }>;
};

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [customToken, setCustomToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();


  // Exchange Firebase token for custom JWT
  const exchangeToken = async (firebaseUser: User) => {
    try {
      const idToken = await firebaseUser.getIdToken();
      
      // Use the centralized API client for token exchange
      const { authApi } = await import('@/lib/api/client');
      const response = await authApi.exchangeToken(idToken);

      if (response.data) {
        const { access_token } = response.data;
        setCustomToken(access_token);
        // Store in token manager (single source of truth)
        tokenManager.setToken(access_token);
        return access_token;
      } else if (response.status === 401 || response.status === 403) {
        // Token exchange failed due to invalid/expired Firebase token
        toast.error('Session expired. Please sign in again.');
        await signOut(auth); // This will trigger cleanup and redirect to login
        return null;
      } else {
        toast.error('Authentication failed. Please try again.');
        return null;
      }
    } catch (error) {
      toast.error('Authentication failed. Please try again.');
      await signOut(auth); // Force logout on any error to prevent stuck loading
      return null;
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        // Exchange Firebase token for custom token
        await exchangeToken(firebaseUser);
        setUser(firebaseUser);
      } else {
        setUser(null);
        setCustomToken(null);
        // Clear token from token manager (single source of truth)
        tokenManager.clearToken();
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const signIn = async (email: string, password: string) => {
    try {
      const { user } = await signInWithEmailAndPassword(auth, email, password);
      if (user) {
        await exchangeToken(user);
        // Don't redirect here - let WorkspaceCheck handle it
      }
      return { error: null };
    } catch (error: any) {
      return { error };
    }
  };

  const signUp = async (email: string, password: string) => {
    try {
      const { user } = await createUserWithEmailAndPassword(auth, email, password);
      if (user) {
        await sendEmailVerification(user);
        await exchangeToken(user);
        router.push('/verify-email');
      }
      return { error: null };
    } catch (error: any) {
      return { error };
    }
  };

  const signInWithGoogle = async () => {
    try {
      const provider = new GoogleAuthProvider();
      const { user } = await signInWithPopup(auth, provider);
      if (user) {
        await exchangeToken(user);
        // Don't redirect here - let WorkspaceCheck handle it
      }
      return { error: null };
    } catch (error: any) {
      return { error };
    }
  };

  const signInWithApple = async () => {
    try {
      const provider = new OAuthProvider('apple.com');
      const { user } = await signInWithPopup(auth, provider);
      if (user) {
        await exchangeToken(user);
        // Don't redirect here - let WorkspaceCheck handle it
      }
      return { error: null };
    } catch (error: any) {
      return { error };
    }
  };

  const signInWithFacebook = async () => {
    try {
      const provider = new FacebookAuthProvider();
      const { user } = await signInWithPopup(auth, provider);
      if (user) {
        await exchangeToken(user);
        // Don't redirect here - let WorkspaceCheck handle it
      }
      return { error: null };
    } catch (error: any) {
      return { error };
    }
  };

  const logout = async () => {
    await signOut(auth);
    setCustomToken(null);
    tokenManager.clearToken();
    
    // Clear ALL user-specific data using centralized storage manager
    userStorage.clearAll();
    
    router.push('/login');
  };

  const resetPassword = async (email: string) => {
    try {
      await sendPasswordResetEmail(auth, email);
      return { error: null };
    } catch (error: any) {
      return { error };
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      customToken,
      loading,
      signIn,
      signUp,
      signInWithGoogle,
      signInWithApple,
      signInWithFacebook,
      logout,
      signOut: logout, // Alias for logout
      resetPassword
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};