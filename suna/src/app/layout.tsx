import type { Metadata } from 'next';
import '@/styles/globals.css';

// Note: Inter font will be loaded via CSS from CDN in production
// For build environments without network access, we use system fonts as fallback

export const metadata: Metadata = {
  title: 'ONYX - Strategic AI Advisor',
  description: 'Your personal strategic AI advisor for founders and executives',
  keywords: ['AI', 'chat', 'advisor', 'strategic planning', 'ONYX'],
  authors: [{ name: 'ONYX Team' }],
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
  themeColor: '#0F172A',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="font-sans">
        {children}
      </body>
    </html>
  );
}
