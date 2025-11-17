import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import RequireAuth from "./components/RequireAuth";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import Home from "./pages/Home";
import BlogAuthorsPage from "./pages/BlogAuthors";
import BlogListPage from "./pages/BlogList";
import TestsPage from "./pages/Tests";
import AuthPage from "./pages/Auth";
import { useSupabaseAuth } from "./providers/AuthProvider";

const queryClient = new QueryClient();

const AuthLayout = ({ children }: { children: ReactNode }) => (
  <div className="flex min-h-screen items-center justify-center bg-background px-4">
    <div className="w-full max-w-xl">{children}</div>
  </div>
);

const HomeRoute = () => {
  const { user, loading } = useSupabaseAuth();
  if (loading) return null;
  if (user) {
    return <Navigate to="/home" replace />;
  }
  return <Index />;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomeRoute />} />
          <Route
            path="/sign-in/*"
            element={
              <AuthLayout>
                <AuthPage mode="sign-in" />
              </AuthLayout>
            }
          />
          <Route
            path="/sign-up/*"
            element={
              <AuthLayout>
                <AuthPage mode="sign-up" />
              </AuthLayout>
            }
          />
          <Route
            path="/home"
            element={
              <RequireAuth redirectTo="/sign-in">
                <Home />
              </RequireAuth>
            }
          />
          <Route
            path="/blog-authors"
            element={
              <RequireAuth redirectTo="/sign-in">
                <BlogAuthorsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/blogs"
            element={
              <RequireAuth redirectTo="/sign-in">
                <BlogListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/tests"
            element={
              <RequireAuth redirectTo="/sign-in">
                <TestsPage />
              </RequireAuth>
            }
          />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
