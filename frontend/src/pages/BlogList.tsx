import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button-enhanced";
import { fetchHubSpotBlogs } from "@/lib/hubspotBlogs";
import { useSupabaseAuth } from "@/providers/AuthProvider";

type Blog = {
  id: string;
  name?: string;
  slug?: string;
  description?: string;
};

const BlogListPage = () => {
  const { user, session, loading } = useSupabaseAuth();
  const navigate = useNavigate();
  const userId = user?.id;
  const accessToken = session?.access_token;

  const [blogs, setBlogs] = useState<Blog[]>([]);
  const [blogsLoading, setBlogsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!userId) {
      setError("Please sign in to view HubSpot blogs.");
      setBlogsLoading(false);
      return;
    }

    let active = true;
    setBlogsLoading(true);
    fetchHubSpotBlogs(userId, accessToken)
      .then((payload) => {
        if (!active) return;
        setBlogs((payload.results ?? []) as Blog[]);
        setError(null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      })
      .finally(() => {
        if (active) setBlogsLoading(false);
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
            <h1 className="text-3xl font-semibold text-foreground">Blogs</h1>
            <p className="text-sm text-muted-foreground">These are the content groups you can publish to.</p>
          </div>
          <Button variant="hero-outline" size="sm" onClick={() => navigate("/home")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to home
          </Button>
        </div>

        {blogsLoading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-card/60 p-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading blogs...
          </div>
        )}

        {!blogsLoading && error && (
          <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-6 text-destructive">
            {error}
          </div>
        )}

        {!blogsLoading && !error && (
          <div className="rounded-2xl border border-border bg-card/60">
            <div className="flex items-center justify-between border-b border-border px-6 py-4 text-sm text-muted-foreground">
              <span>{blogs.length} blogs</span>
            </div>
            <div className="divide-y divide-border">
              {blogs.length === 0 && (
                <p className="px-6 py-8 text-center text-sm text-muted-foreground">No blogs returned for this portal.</p>
              )}
              {blogs.map((blog) => (
                <div key={blog.id} className="flex flex-col gap-2 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-base font-semibold text-foreground">{blog.name || `Blog ${blog.id}`}</p>
                    <p className="text-sm text-muted-foreground">{blog.description || "No description provided."}</p>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p className="font-mono text-xs text-foreground">ID: {blog.id}</p>
                    {blog.slug && <p>Slug: {blog.slug}</p>}
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

export default BlogListPage;
