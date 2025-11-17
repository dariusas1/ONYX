/**
 * NextAuth Configuration and Route Handler
 *
 * This module implements OAuth2 authentication with Google as the identity provider.
 * Handles session management and token storage for Google Workspace API access.
 */

import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import type { NextAuthOptions, DefaultSession } from "next-auth";

// Extend NextAuth default types
declare module "next-auth" {
  interface Session {
    user?: {
      id: string;
      email?: string | null;
      name?: string | null;
      isAdmin?: boolean;
      accessToken?: string;
      refreshToken?: string;
      expiresAt?: number;
      scopes?: string[];
    };
  }

  interface JWT {
    sub?: string;
    accessToken?: string;
    refreshToken?: string;
    expiresAt?: number;
    scopes?: string[];
  }
}

/**
 * NextAuth Configuration
 *
 * - Implements OAuth2 Authorization Code Flow
 * - Uses JWT-based sessions
 * - Stores encrypted tokens via backend API
 */
export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
      allowDangerousEmailAccountLinking: false,
      authorization: {
        params: {
          scope: [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
          ].join(" "),
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
  ],
  callbacks: {
    /**
     * JWT Callback
     *
     * Called whenever JWT is created or updated.
     * Stores encrypted tokens from OAuth account for later use.
     */
    async jwt({ token, account }) {
      // Store tokens from initial OAuth response
      if (account) {
        // Call backend to store and encrypt tokens
        try {
          await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/google-drive/auth/callback`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${process.env.NEXTAUTH_SECRET}`,
              },
              body: JSON.stringify({
                code: account.access_token, // Note: In real flow, this would be auth code
                state: token.sub,
              }),
            }
          );

          token.accessToken = account.access_token;
          token.refreshToken = account.refresh_token;
          token.expiresAt = account.expires_at ? account.expires_at * 1000 : undefined;
          token.scopes = account.scope?.split(" ") || [];
        } catch (error) {
          console.error("Failed to store OAuth tokens:", error);
        }
      }

      // Check if token refresh needed
      if (token.expiresAt && typeof token.expiresAt === "number" && Date.now() < token.expiresAt) {
        return token;
      }

      // Token refresh logic - call backend
      if (token.refreshToken) {
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/google-drive/auth/refresh`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token.sub}`,
              },
              body: JSON.stringify({
                refreshToken: token.refreshToken,
              }),
            }
          );

          if (response.ok) {
            const refreshResponse = await response.json();
            token.accessToken = refreshResponse.data.accessToken;
            token.expiresAt = refreshResponse.data.expiresAt;
          }
        } catch (error) {
          console.error("Failed to refresh token:", error);
        }
      }

      return token;
    },

    /**
     * Session Callback
     *
     * Called when session is retrieved on client side.
     * Exposes token data to client-side useSession() hook.
     */
    async session({ session, token }) {
      if (session && session.user) {
        session.user.id = token.sub || "";
        session.user.accessToken = token.accessToken as string;
        session.user.expiresAt = token.expiresAt as number;
        session.user.scopes = token.scopes as string[];
      }
      return session;
    },

    /**
     * Redirect Callback
     *
     * Controls where user is redirected after signin/error.
     */
    async redirect({ url, baseUrl }) {
      // Redirect to dashboard after successful login
      if (url.startsWith(baseUrl)) {
        return url;
      }
      return baseUrl;
    },

    /**
     * SignIn Callback
     *
     * Controls whether user can sign in.
     */
    async signIn({ account }) {
      // Ensure refresh token was provided
      if (!account?.refresh_token) {
        console.warn(
          "No refresh token received from Google. User may need to grant offline access."
        );
      }

      return true;
    },
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60, // 24 hours
  },
  jwt: {
    secret: process.env.NEXTAUTH_SECRET,
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  debug: process.env.NODE_ENV === "development",
};

/**
 * NextAuth Handler
 *
 * Exports the dynamic route handler for NextAuth
 */
const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
