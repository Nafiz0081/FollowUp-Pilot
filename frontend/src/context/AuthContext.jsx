import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { onAuthStateChanged, signOut as firebaseSignOut } from "firebase/auth";
import { auth } from "../firebase";
import { api } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshProfile = useCallback(async () => {
    if (!auth.currentUser) {
      setProfile(null);
      return;
    }
    try {
      const me = await api.me();
      setProfile(me);
    } catch {
      setProfile(null);
    }
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        await refreshProfile();
      } else {
        setProfile(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, [refreshProfile]);

  const signOut = () => firebaseSignOut(auth);

  const value = {
    user,
    profile,
    loading,
    isAdmin: Boolean(profile?.is_admin),
    isRegistered: Boolean(profile?.name),
    refreshProfile,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
