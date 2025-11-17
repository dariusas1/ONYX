import { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"

// Extend the built-in session types
declare module "next-auth" {
  interface Session {
    user?: {
      id?: string
      email?: string | null
      name?: string | null
      isAdmin?: boolean
      accessToken?: string
      refreshToken?: string
      expiresAt?: number
      scopes?: string[]
    }
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id?: string
    isAdmin?: boolean
    accessToken?: string
    refreshToken?: string
    expiresAt?: number
    scopes?: string[]
  }
}

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
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // This is a placeholder - in a real implementation, you would
        // verify credentials against your database
        if (credentials?.email && credentials?.password) {
          return {
            id: "1",
            email: credentials.email,
            name: "Demo User",
            isAdmin: false
          }
        }
        return null
      }
    })
  ],
  session: {
    strategy: "jwt"
  },
  callbacks: {
    /**
     * JWT Callback
     *
     * Called whenever JWT is created or updated.
     * Handles token refresh logic and stores tokens from OAuth account.
     *
     * ISSUE 1 FIX: Restructured token refresh logic
     * - Checks if token is expired OR within 1-hour expiry buffer
     * - Attempts refresh via backend endpoint
     * - Handles refresh success/failure gracefully
     *
     * ISSUE 2 FIX: Changed to pass authorization code to backend
     * - Backend exchanges code for tokens via Google's OAuth endpoint
     * - Backend encrypts and stores tokens in oauth_tokens table
     * - NextAuth also stores tokens in JWT for session management
     */
    async jwt({ token, account, user }: any) {
      // Handle credentials provider (no account object)
      if (user && typeof user === 'object') {
        token.id = (user as any).id
        token.isAdmin = (user as any).isAdmin
      }

      // Store tokens from initial OAuth response (when account object is present)
      if (account) {
        // Call backend to exchange authorization code and store encrypted tokens
        // The backend will use the authorization code to get tokens from Google
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
                code: account.code, // ISSUE 2 FIX: Pass authorization code (not access_token)
                state: token.sub, // CSRF protection: state = user ID
              }),
            }
          );

          // Store tokens from NextAuth's account object in JWT for client-side use
          token.accessToken = account.access_token;
          token.refreshToken = account.refresh_token;
          token.expiresAt = account.expires_at ? account.expires_at * 1000 : undefined;
          token.scopes = account.scope?.split(" ") || [];
        } catch (error) {
          console.error("Failed to store OAuth tokens in backend:", error);
          // Continue even if backend storage fails - JWT storage is still valid
          // Backend storage is for encrypted persistence; JWT is the primary storage
        }
      }

      // ISSUE 1 FIX: Proper token refresh logic
      // Check if token needs refresh (expired OR within 1-hour expiry buffer)
      const needsRefresh = !token.expiresAt ||
        typeof token.expiresAt !== "number" ||
        (Date.now() + 3600000) >= token.expiresAt; // 3600000 ms = 1 hour

      if (needsRefresh && token.refreshToken) {
        // Attempt to refresh the token via backend endpoint
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
            // Update token with refreshed values
            token.accessToken = refreshResponse.data.accessToken;
            token.expiresAt = refreshResponse.data.expiresAt;
          } else {
            console.warn(
              `Token refresh failed with status ${response.status}: returning original token`
            );
            // Return original token if refresh fails - it may still be valid for now
          }
        } catch (error) {
          console.error("Failed to refresh token:", error);
          // Return original token if refresh fails - it may still be valid for now
        }
      }

      return token
    },
    /**
     * Session Callback
     *
     * Called when session is retrieved on client side.
     * Exposes token data to client-side useSession() hook.
     */
    async session({ session, token }) {
      if (token && session.user) {
        session.user.id = token.id
        session.user.isAdmin = token.isAdmin
        session.user.accessToken = token.accessToken
        session.user.expiresAt = token.expiresAt
        session.user.scopes = token.scopes
      }
      return session
    }
  },
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error"
  }
}

// Helper function to get server session
export async function getServerSession() {
  // This would typically use getServerSession from next-auth/next
  // For now, returning a mock session for development
  return {
    user: {
      id: "demo-user-id",
      email: "demo@example.com",
      name: "Demo User",
      isAdmin: false
    },
    expires: "2024-12-31T23:59:59.999Z"
  }
}
