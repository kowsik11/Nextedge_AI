import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button-enhanced";
import { fetchHubSpotBlogAuthors } from "@/lib/hubspotAuthors";
import { cn } from "@/lib/utils";
import { useSupabaseAuth } from "@/providers/AuthProvider";

type Author = {
  id: string | number;
  display_name?: string;
  name?: string;
  email?: string;
  bio?: string;
};

const BlogAuthorsPage = () => {
  const { user, session, loading } = useSupabaseAuth();
  const navigate = useNavigate();
  const userId = user?.id;
  const accessToken = session?.access_token;
  const [authors, setAuthors] = useState<Author[]>([]);
  const [authorsLoading, setAuthorsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!userId) {
      setError("Please sign in to view HubSpot authors.");
      setAuthorsLoading(false);
      return;
    }

    let active = true;
    setAuthorsLoading(true);
    setError(null);
    fetchHubSpotBlogAuthors(userId, accessToken)
      .then((payload) => {
        if (!active) return;
        const items = (payload.results ?? []) as Author[];
        setAuthors(items);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      })
      .finally(() => {
        if (active) setAuthorsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [accessToken, loading, userId]);

  return (
    <div className="min-h-screen bg-background px-6 py-8">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">HubSpot</p>
            <h1 className="text-3xl font-semibold text-foreground">Blog authors</h1>
            <p className="text-sm text-muted-foreground">Fetched directly from /cms/v3/blog-authors.</p>
          </div>
          <Button variant="hero-outline" size="sm" onClick={() => navigate("/home")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to home
          </Button>
        </div>

        {authorsLoading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-card/60 p-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading authors...
          </div>
        )}

        {!authorsLoading && error && (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-6 text-destructive">
            {error}
          </div>
        )}

        {!authorsLoading && !error && (
          <div className="rounded-2xl border border-border bg-card/60">
            <div className="flex items-center justify-between border-b border-border px-6 py-4 text-sm text-muted-foreground">
              <span>{authors.length} authors</span>
            </div>
            <div className="divide-y divide-border">
              {authors.length === 0 && (
                <p className="px-6 py-8 text-center text-sm text-muted-foreground">No authors returned for this portal.</p>
              )}
              {authors.map((author) => (
                <div key={author.id} className="flex flex-col gap-2 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-base font-semibold text-foreground">{author.display_name || author.name || `Author ${author.id}`}</p>
                    <p className="text-sm text-muted-foreground">{author.bio || "No bio provided."}</p>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p className={cn("font-mono text-xs", "text-foreground")}>ID: {author.id}</p>
                    {author.email && <p>{author.email}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BlogAuthorsPage;
