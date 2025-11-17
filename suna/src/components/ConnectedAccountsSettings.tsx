/**
 * Connected Accounts Settings Component
 *
 * Displays connected third-party accounts (Google, etc.) with disconnect functionality.
 * Part of the user settings/profile page.
 */

"use client";

import React, { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Trash2, Check, AlertCircle, Loader } from "lucide-react";

interface ConnectedAccount {
  provider: string;
  email: string;
  connectedAt: string;
  scopes: string[];
  status: "connected" | "disconnected" | "error";
}

/**
 * ConnectedAccountsSettings Component
 *
 * Shows user's connected OAuth accounts and provides disconnect option.
 */
export const ConnectedAccountsSettings: React.FC = () => {
  const { data: session, status } = useSession();
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  /**
   * Fetch connected accounts on component mount
   */
  useEffect(() => {
    if (status === "authenticated") {
      fetchConnectedAccounts();
    }
  }, [session, status]);

  /**
   * Fetch list of connected accounts from backend
   */
  const fetchConnectedAccounts = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("/api/auth/accounts", {
        headers: {
          Authorization: `Bearer ${session?.user?.accessToken || ""}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch connected accounts");
      }

      const data = await response.json();
      setAccounts(data.data || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);
      console.error("Failed to fetch connected accounts:", err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle account disconnection
   */
  const handleDisconnect = async (provider: string) => {
    if (
      !window.confirm(
        `Are you sure you want to disconnect your ${provider} account? You won't be able to sync files from this provider until you reconnect.`
      )
    ) {
      return;
    }

    try {
      setDisconnecting(provider);
      setError(null);
      setSuccessMessage(null);

      const response = await fetch("/api/auth/revoke", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.user?.accessToken || ""}`,
        },
        body: JSON.stringify({ provider }),
      });

      if (!response.ok) {
        throw new Error("Failed to disconnect account");
      }

      // Update local state
      setAccounts((prev) =>
        prev.map((acc) =>
          acc.provider === provider
            ? { ...acc, status: "disconnected" }
            : acc
        )
      );

      setSuccessMessage(`${provider} account disconnected successfully`);

      // Clear message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);
      console.error("Failed to disconnect account:", err);
    } finally {
      setDisconnecting(null);
    }
  };

  /**
   * Format provider name for display
   */
  const formatProviderName = (provider: string): string => {
    const names: Record<string, string> = {
      google_drive: "Google Drive",
      google_workspace: "Google Workspace",
      slack: "Slack",
      github: "GitHub",
    };
    return names[provider] || provider;
  };

  /**
   * Format date for display
   */
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateString;
    }
  };

  /**
   * Render loading state
   */
  if (loading && status === "authenticated") {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-3">
          <Loader className="h-5 w-5 animate-spin text-gray-400" />
          <span className="text-gray-600">Loading connected accounts...</span>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <div className="flex-1">
            <h3 className="font-medium text-red-900">Error Loading Accounts</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
            <button
              onClick={fetchConnectedAccounts}
              className="mt-2 text-sm font-medium text-red-700 hover:text-red-800 underline"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  /**
   * Render no accounts state
   */
  if (accounts.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
        <p className="text-gray-600">No connected accounts yet.</p>
        <p className="mt-1 text-sm text-gray-500">
          Connect a service to enable file syncing and integrations.
        </p>
      </div>
    );
  }

  /**
   * Render connected accounts list
   */
  return (
    <div className="space-y-4">
      {/* Success message */}
      {successMessage && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="flex items-start gap-3">
            <Check className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-green-700">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Accounts list */}
      <div className="space-y-3">
        {accounts.map((account) => (
          <div
            key={account.provider}
            className="rounded-lg border border-gray-200 bg-white p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900">
                    {formatProviderName(account.provider)}
                  </h3>
                  {account.status === "connected" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
                      <span className="h-2 w-2 rounded-full bg-green-600" />
                      Connected
                    </span>
                  )}
                  {account.status === "disconnected" && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">
                      <span className="h-2 w-2 rounded-full bg-gray-400" />
                      Disconnected
                    </span>
                  )}
                </div>

                {/* Account email */}
                <p className="mt-1 text-sm text-gray-600">{account.email}</p>

                {/* Connected date */}
                <p className="mt-0.5 text-xs text-gray-500">
                  Connected on {formatDate(account.connectedAt)}
                </p>

                {/* Scopes */}
                {account.scopes && account.scopes.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-medium text-gray-700">
                      Permissions:
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {account.scopes.map((scope) => (
                        <span
                          key={scope}
                          className="inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                        >
                          {scope
                            .split("/")
                            .pop()
                            ?.replace(/^auth\//, "")
                            .replace(/_/g, " ") || scope}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Disconnect button */}
              {account.status === "connected" && (
                <button
                  onClick={() => handleDisconnect(account.provider)}
                  disabled={disconnecting === account.provider}
                  className="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {disconnecting === account.provider ? (
                    <>
                      <Loader className="h-4 w-4 animate-spin" />
                      <span>Disconnecting...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="h-4 w-4" />
                      <span>Disconnect</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConnectedAccountsSettings;
