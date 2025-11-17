/**
 * Google Sign-In Button Component
 *
 * Provides a branded Google sign-in button with loading and error states.
 * Integrates with NextAuth for OAuth2 authentication flow.
 */

"use client";

import React, { useState } from "react";
import { signIn } from "next-auth/react";
import { LogIn } from "lucide-react";

interface GoogleSignInButtonProps {
  /** Text to display in button */
  label?: string;
  /** Callback on successful sign-in */
  onSuccess?: () => void;
  /** Callback on sign-in error */
  onError?: (error: string) => void;
  /** Optional CSS class name */
  className?: string;
  /** Disable button */
  disabled?: boolean;
}

/**
 * GoogleSignInButton Component
 *
 * Renders a branded Google sign-in button with loading state.
 * Handles OAuth flow via NextAuth signIn() function.
 */
export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  label = "Sign in with Google",
  onSuccess,
  onError,
  className = "",
  disabled = false,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle sign-in click
   *
   * Initiates OAuth2 flow with Google provider.
   */
  const handleSignIn = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Redirect to Google OAuth consent screen
      const result = await signIn("google", {
        redirect: true,
        callbackUrl: "/dashboard",
      });

      // signIn with redirect=true will redirect, but handle error case
      if (result?.error) {
        const errorMessage = getErrorMessage(result.error);
        setError(errorMessage);
        onError?.(errorMessage);
      } else if (result?.ok || result === undefined) {
        // redirect=true means result will be undefined if successful (page redirects)
        onSuccess?.();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Sign-in failed";
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Get user-friendly error message
   */
  const getErrorMessage = (error: string): string => {
    const errorMap: Record<string, string> = {
      Callback: "Invalid callback URL",
      OAuthCallback: "OAuth callback failed",
      OAuthAccountNotLinked:
        "Email already exists with different provider",
      EmailCreateAccount: "Failed to create account",
      SessionCallback: "Session error",
      Default: "Authentication failed",
    };

    return errorMap[error] || errorMap.Default;
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={handleSignIn}
        disabled={isLoading || disabled}
        className={`
          relative inline-flex items-center justify-center gap-2
          rounded-lg bg-white px-6 py-3
          border border-gray-300 shadow-sm
          font-medium text-gray-700
          transition-all duration-200
          hover:bg-gray-50 hover:border-gray-400 hover:shadow-md
          active:bg-gray-100
          disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-white disabled:hover:shadow-sm
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${className}
        `}
        aria-label="Sign in with Google"
      >
        {/* Google Logo */}
        <svg
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <path
            d="M20.283 10.356h-8.327v3.057h4.694c-.275 1.371-1.527 4.106-4.694 4.106-2.834 0-5.153-2.354-5.153-5.25 0-2.895 2.318-5.25 5.153-5.25 1.616 0 3.062.617 4.1 1.594l2.426-2.343C16.974 2.705 13.834 0 10.242 0 4.58 0 0 4.58 0 10.25c0 5.669 4.58 10.25 10.242 10.25 5.934 0 9.868-4.144 9.868-9.975 0-.665-.066-1.344-.202-2.119z"
            fill="#4285F4"
          />
        </svg>

        {/* Loading spinner or label */}
        {isLoading ? (
          <>
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
            <span>Signing in...</span>
          </>
        ) : (
          <>
            <LogIn className="h-4 w-4" />
            <span>{label}</span>
          </>
        )}
      </button>

      {/* Error message */}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          <p className="font-medium">Authentication Error</p>
          <p className="mt-1">{error}</p>
        </div>
      )}
    </div>
  );
};

export default GoogleSignInButton;
