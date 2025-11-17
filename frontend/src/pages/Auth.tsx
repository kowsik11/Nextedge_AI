import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button-enhanced";
import { Input } from "@/components/ui/input";
import { useSupabaseAuth } from "@/providers/AuthProvider";
import { toast } from "@/hooks/use-toast";

export type AuthMode = "sign-in" | "sign-up";

const labels: Record<AuthMode, { title: string; cta: string; switchText: string; switchTo: AuthMode }> = {
  "sign-in": { title: "Sign in", cta: "Sign in", switchText: "Need an account?", switchTo: "sign-up" },
  "sign-up": { title: "Create account", cta: "Sign up", switchText: "Already have an account?", switchTo: "sign-in" },
};

export default function AuthPage({ mode }: { mode: AuthMode }) {
  const { signIn, signUp } = useSupabaseAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const { title, cta, switchText, switchTo } = labels[mode];

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    const normalizedEmail = email.trim();
    const fn = mode === "sign-in" ? signIn : signUp;
    const { error } = await fn(normalizedEmail, password);
    setLoading(false);
    if (error) {
      toast({ title: "Authentication failed", description: error, variant: "destructive" });
      return;
    }
    toast({ title: "Success", description: mode === "sign-in" ? "Signed in" : "Account created" });
    navigate("/home");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card/80 p-6 shadow-card">
        <h1 className="text-2xl font-semibold text-foreground">{title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Use your Supabase credentials to continue.</p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="space-y-1 text-sm text-foreground">
            Email
            <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 focus-within:border-primary">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <Input
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
              />
            </div>
          </label>

          <label className="space-y-1 text-sm text-foreground">
            Password
            <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2 focus-within:border-primary">
              <Lock className="h-4 w-4 text-muted-foreground" />
              <Input
                type="password"
                autoComplete={mode === "sign-up" ? "new-password" : "current-password"}
                placeholder="••••••••"
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
              />
            </div>
          </label>

          <Button type="submit" variant="hero" className="w-full" disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : cta}
          </Button>
        </form>

        <div className="mt-4 text-center text-sm text-muted-foreground">
          {switchText}{" "}
          <Link className="text-primary underline" to={switchTo === "sign-in" ? "/sign-in" : "/sign-up"}>
            {switchTo === "sign-in" ? "Sign in" : "Create one"}
          </Link>
        </div>
      </div>
    </div>
  );
}
