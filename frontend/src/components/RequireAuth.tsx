import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useSupabaseAuth } from "@/providers/AuthProvider";

const RequireAuth = ({ children, redirectTo = "/sign-in" }: { children: ReactNode; redirectTo?: string }) => {
  const { user, loading } = useSupabaseAuth();

  if (loading) {
    return null;
  }

  if (!user) {
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
};

export default RequireAuth;
