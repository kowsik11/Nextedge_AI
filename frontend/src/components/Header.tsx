import React, { useState } from "react";
import { Button } from "./ui/button-enhanced";
import { Menu, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useSupabaseAuth } from "@/providers/AuthProvider";

const Header = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { user, signOut } = useSupabaseAuth();
  const navigate = useNavigate();

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 max-w-7xl items-center justify-between">
        <div className="flex items-center">
          <img
            src="/lovable-uploads/adc57d85-0a2e-43b2-91d1-45cf3e175ec3.png"
            alt="NEXTEDGE"
            className="h-8 w-auto"
          />
        </div>

        <nav className="hidden items-center space-x-8 md:flex">
          <a href="#product" className="text-sm font-medium text-foreground transition-colors hover:text-primary">
            Product
          </a>
          <a href="#integrations" className="text-sm font-medium text-foreground transition-colors hover:text-primary">
            Integrations
          </a>
          <a href="#pricing" className="text-sm font-medium text-foreground transition-colors hover:text-primary">
            Pricing
          </a>
          <a href="#security" className="text-sm font-medium text-foreground transition-colors hover:text-primary">
            Security
          </a>
          <a href="#contact" className="text-sm font-medium text-foreground transition-colors hover:text-primary">
            Contact
          </a>
        </nav>

        <div className="hidden items-center space-x-4 md:flex">
          {!user && (
            <>
              <Button variant="nav" size="sm" asChild>
                <Link to="/sign-in">Login</Link>
              </Button>
              <Button variant="hero" size="sm" asChild>
                <Link to="/sign-up">Sign Up</Link>
              </Button>
              <Button variant="hero" size="sm">
                Book a Demo
              </Button>
            </>
          )}
          {user && (
            <>
              <Button variant="hero" size="sm">
                Book a Demo
              </Button>
              <Button variant="outline" size="sm" onClick={handleSignOut}>
                Sign out
              </Button>
            </>
          )}
        </div>

        <button onClick={toggleMenu} className="p-2 text-foreground hover:text-primary md:hidden" aria-label="Toggle menu">
          {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {isMenuOpen && (
        <div className="border-t bg-background/95 backdrop-blur md:hidden">
          <nav className="container space-y-4 py-4">
            <a href="#product" className="block text-sm font-medium text-foreground transition-colors hover:text-primary">
              Product
            </a>
            <a href="#integrations" className="block text-sm font-medium text-foreground transition-colors hover:text-primary">
              Integrations
            </a>
            <a href="#pricing" className="block text-sm font-medium text-foreground transition-colors hover:text-primary">
              Pricing
            </a>
            <a href="#security" className="block text-sm font-medium text-foreground transition-colors hover:text-primary">
              Security
            </a>
            <a href="#contact" className="block text-sm font-medium text-foreground transition-colors hover:text-primary">
              Contact
            </a>
            <div className="flex flex-col space-y-3 border-t pt-4">
              {!user && (
                <>
                  <Button variant="nav" size="sm" asChild>
                    <Link to="/sign-in">Login</Link>
                  </Button>
                  <Button variant="hero" size="sm" asChild>
                    <Link to="/sign-up">Sign Up</Link>
                  </Button>
                  <Button variant="hero" size="sm">
                    Book a Demo
                  </Button>
                </>
              )}
              {user && (
                <>
                  <Button variant="hero" size="sm">
                    Book a Demo
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleSignOut}>
                    Sign out
                  </Button>
                </>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;
