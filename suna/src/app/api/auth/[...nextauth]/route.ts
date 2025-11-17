/**
 * NextAuth Dynamic Route Handler
 *
 * This module exports the NextAuth handler as the dynamic route
 * for the [...nextauth] catch-all route.
 */

import NextAuth from "next-auth"
import { authOptions } from "@/lib/auth"

const handler = NextAuth(authOptions)

export const GET = handler
export const POST = handler
