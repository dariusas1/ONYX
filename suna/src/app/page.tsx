import React from 'react';
import { Header } from '@/components/Header';
import { ChatInterface } from '@/components/ChatInterface';

export interface ChatPageProps {
  searchParams: { conversationId?: string };
}

export default function ChatPage({ searchParams }: ChatPageProps) {
  return (
    <main className="h-screen flex flex-col bg-manus-bg">
      <Header />
      <ChatInterface conversationId={searchParams.conversationId} />
    </main>
  );
}
