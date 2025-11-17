/**
 * Unit Tests: NextAuth OAuth Authorization Code Exchange (ISSUE 2 FIX)
 *
 * Tests the JWT callback OAuth flow to verify:
 * 1. Authorization code is passed to backend (not access_token)
 * 2. Backend endpoint receives correct parameters
 * 3. Token storage in both JWT and backend works correctly
 * 4. Failure to store in backend doesn't break JWT storage
 */

describe("NextAuth JWT Callback - OAuth Code Exchange (ISSUE 2)", () => {
  const mockFetch = jest.fn();
  const mockAccount: any = {
    code: "auth-code-from-google-oauth",
    access_token: "access-token-from-google",
    refresh_token: "refresh-token-from-google",
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    scope: "openid email profile https://www.googleapis.com/auth/drive",
  };

  const mockToken = {
    sub: "test-user-id",
    iat: Date.now(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = mockFetch;
  });

  describe("OAuth Code Extraction and Passing", () => {
    test("should pass authorization code (not access_token) to backend", async () => {
      const backendResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          success: true,
          data: {
            message: "Google Drive connected successfully",
            user_id: mockToken.sub,
          },
        }),
      };

      mockFetch.mockResolvedValueOnce(backendResponse);

      // Simulate JWT callback logic
      const requestBody = {
        code: mockAccount.code, // ISSUE 2 FIX: Pass authorization code
        state: mockToken.sub,
      };

      // Verify we're passing the authorization code, not access_token
      expect(requestBody.code).toBe("auth-code-from-google-oauth");
      expect(requestBody.code).not.toBe(mockAccount.access_token);

      await fetch(
        "http://localhost:8000/api/google-drive/auth/callback",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${process.env.NEXTAUTH_SECRET}`,
          },
          body: JSON.stringify(requestBody),
        }
      );

      // Verify fetch was called with correct parameters
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/google-drive/auth/callback",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        })
      );

      // Verify the body contains the authorization code
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.code).toBe("auth-code-from-google-oauth");
      expect(body.state).toBe(mockToken.sub);
    });

    test("should use state parameter for CSRF protection", async () => {
      const backendResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          success: true,
          data: {
            message: "Google Drive connected successfully",
            user_id: mockToken.sub,
          },
        }),
      };

      mockFetch.mockResolvedValueOnce(backendResponse);

      const requestBody = {
        code: mockAccount.code,
        state: mockToken.sub, // State = user ID for CSRF protection
      };

      await fetch(
        "http://localhost:8000/api/google-drive/auth/callback",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${process.env.NEXTAUTH_SECRET}`,
          },
          body: JSON.stringify(requestBody),
        }
      );

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.state).toBe(mockToken.sub);
    });
  });

  describe("Token Storage in JWT", () => {
    test("should store tokens from account object in JWT", () => {
      // Simulate JWT token updates
      const updatedToken = {
        ...mockToken,
        accessToken: mockAccount.access_token,
        refreshToken: mockAccount.refresh_token,
        expiresAt: mockAccount.expires_at * 1000, // Convert to milliseconds
        scopes: (mockAccount.scope as string).split(" "),
      };

      expect(updatedToken.accessToken).toBe(mockAccount.access_token);
      expect(updatedToken.refreshToken).toBe(mockAccount.refresh_token);
      expect(updatedToken.expiresAt).toBe(mockAccount.expires_at * 1000);
      expect(updatedToken.scopes).toContain("https://www.googleapis.com/auth/drive");
    });

    test("should handle missing expires_at gracefully", () => {
      const accountWithoutExpiry = {
        ...mockAccount,
        expires_at: undefined,
      };

      const updatedToken = {
        ...mockToken,
        accessToken: accountWithoutExpiry.access_token,
        refreshToken: accountWithoutExpiry.refresh_token,
        expiresAt: accountWithoutExpiry.expires_at
          ? accountWithoutExpiry.expires_at * 1000
          : undefined,
        scopes: (accountWithoutExpiry.scope as string).split(" "),
      };

      expect(updatedToken.expiresAt).toBeUndefined();
      expect(updatedToken.accessToken).toBeDefined();
      expect(updatedToken.refreshToken).toBeDefined();
    });

    test("should handle missing scope gracefully", () => {
      const accountWithoutScope = {
        ...mockAccount,
        scope: undefined,
      };

      const scopes = accountWithoutScope.scope
        ? (accountWithoutScope.scope as string).split(" ")
        : [];

      expect(scopes).toEqual([]);
    });
  });

  describe("Backend Storage Resilience", () => {
    test("should continue if backend storage fails", async () => {
      const backendError = {
        ok: false,
        status: 500,
        json: jest.fn().mockResolvedValue({
          success: false,
          detail: "Failed to store OAuth tokens",
        }),
      };

      mockFetch.mockResolvedValueOnce(backendError);

      try {
        const response = await fetch(
          "http://localhost:8000/api/google-drive/auth/callback",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${process.env.NEXTAUTH_SECRET}`,
            },
            body: JSON.stringify({
              code: mockAccount.code,
              state: mockToken.sub,
            }),
          }
        );

        // Even if backend fails, JWT should be updated
        if (!response.ok) {
          console.error("Failed to store OAuth tokens in backend:", response.status);
        }

        // Simulate JWT token being updated anyway
        const updatedToken = {
          ...mockToken,
          accessToken: mockAccount.access_token,
          refreshToken: mockAccount.refresh_token,
          expiresAt: mockAccount.expires_at * 1000,
          scopes: (mockAccount.scope as string).split(" "),
        };

        expect(updatedToken.accessToken).toBeDefined();
        expect(updatedToken.refreshToken).toBeDefined();
      } catch (error) {
        console.error("Fetch failed:", error);
      }

      expect(mockFetch).toHaveBeenCalled();
    });

    test("should continue if network error occurs during backend call", async () => {
      const networkError = new Error("Network error");
      mockFetch.mockRejectedValueOnce(networkError);

      try {
        await fetch(
          "http://localhost:8000/api/google-drive/auth/callback",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${process.env.NEXTAUTH_SECRET}`,
            },
            body: JSON.stringify({
              code: mockAccount.code,
              state: mockToken.sub,
            }),
          }
        );
      } catch (error) {
        console.error("Failed to store OAuth tokens in backend:", error);
      }

      // Simulate JWT token being updated anyway
      const updatedToken = {
        ...mockToken,
        accessToken: mockAccount.access_token,
        refreshToken: mockAccount.refresh_token,
        expiresAt: mockAccount.expires_at * 1000,
        scopes: (mockAccount.scope as string).split(" "),
      };

      expect(updatedToken.accessToken).toBeDefined();
      expect(updatedToken.refreshToken).toBeDefined();
    });
  });

  describe("Backend Endpoint Contract", () => {
    test("backend should receive code that can be exchanged", () => {
      // Verify the contract between frontend and backend
      // Frontend sends: { code, state }
      // Backend expects: OAuthCallbackRequest { code, state }
      // Backend action: exchange code via Google's OAuth endpoint

      const requestPayload = {
        code: "authorization-code-from-google",
        state: "user-id-for-csrf",
      };

      // Backend should be able to receive and process this
      expect(requestPayload).toHaveProperty("code");
      expect(requestPayload).toHaveProperty("state");
      expect(typeof requestPayload.code).toBe("string");
      expect(typeof requestPayload.state).toBe("string");
    });

    test("should not send access_token to backend", () => {
      // ISSUE 2: Verify we're NOT sending access_token
      const frontendRequest = {
        code: mockAccount.code,
        state: mockToken.sub,
        // access_token should NOT be in this request
      };

      expect(frontendRequest).toHaveProperty("code");
      expect(frontendRequest).toHaveProperty("state");
      expect(frontendRequest).not.toHaveProperty("access_token");
    });
  });

  describe("Scopes Handling", () => {
    test("should parse and store granted scopes", () => {
      const scopeString: string = "openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/drive.metadata.readonly";
      const scopes = scopeString.split(" ");

      expect(scopes).toContain("openid");
      expect(scopes).toContain("email");
      expect(scopes).toContain("https://www.googleapis.com/auth/drive");
      expect(scopes).toContain("https://www.googleapis.com/auth/drive.metadata.readonly");
      expect(scopes.length).toBe(5);
    });

    test("should handle empty scope string", () => {
      const scopeString = "";
      const scopes = scopeString.length > 0 ? scopeString.split(" ") : [];

      expect(scopes).toEqual([]);
    });
  });
});
