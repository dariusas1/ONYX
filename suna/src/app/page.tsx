import React from 'react';
import { Header } from '@/components/Header';
import { ChatInterface } from '@/components/ChatInterface';

export interface ChatPageProps {
  searchParams: { conversationId?: string };
}

export default function ChatPage({ searchParams }: ChatPageProps) {
  return (
    <>
      {/* Skip to main content link for screen readers */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 z-50 bg-manus-accent text-white px-4 py-2 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-manus-bg"
      >
        Skip to main content
      </a>

      <main className="h-screen flex flex-col bg-manus-bg" id="main-content">
        <Header />
        <ChatInterface conversationId={searchParams.conversationId} />
      </main>
    </>
  );
}
