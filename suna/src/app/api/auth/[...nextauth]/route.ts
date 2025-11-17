/**
 * NextAuth Dynamic Route Handler
 *
 * This module exports the NextAuth handler as the dynamic route
 * for the [...nextauth] catch-all route.
 *
 * The authOptions are imported from @/lib/auth where the OAuth2
 * authentication flow is configured with:
 * - Google OAuth2 provider setup
 * - JWT callback with token refresh logic (ISSUE 1 FIX)
 * - Backend integration for authorization code exchange (ISSUE 2 FIX)
 */

import NextAuth from "next-auth"
import { authOptions } from "@/lib/auth"

const handler = NextAuth(authOptions)

export const GET = handler
export const POST = handler
