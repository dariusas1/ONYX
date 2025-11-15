import type { Metadata } from 'next';
import '@/styles/globals.css';
import { PerformanceMonitor } from '@/components/PerformanceMonitor';
import { AgentModeProvider } from '@/components/AgentModeProvider';

// Configure Inter font with Next.js Font Optimization
// For environments without network access, set NEXT_PUBLIC_SKIP_FONTS=true
// and the build will use system fonts as fallback
const useGoogleFonts = process.env.NEXT_PUBLIC_SKIP_FONTS !== 'true';

let inter: { className: string };

if (useGoogleFonts) {
  const { Inter } = require('next/font/google');
  inter = Inter({
    subsets: ['latin'],
    weight: ['400', '500', '600', '700'],
    display: 'swap',
    variable: '--font-inter',
    fallback: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
    adjustFontFallback: true,
  });
} else {
  // Use system fonts for offline builds
  inter = { className: 'font-sans' };
}

export const metadata: Metadata = {
  title: 'ONYX - Strategic AI Advisor',
  description: 'Your personal strategic AI advisor for founders and executives. Engage in strategic conversations with system intelligence through a professional, accessible interface.',
  keywords: ['AI', 'chat', 'advisor', 'strategic planning', 'ONYX', 'business intelligence'],
  authors: [{ name: 'ONYX Team' }],
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5, // Allow zooming for accessibility
    userScalable: true,
  },
  themeColor: '#0F172A',
  colorScheme: 'dark',
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/manifest.json',
  robots: 'noindex, nofollow',
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'format-detection': 'telephone=no',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const handleMetricsUpdate = (metrics: any) => {
    // You can send metrics to analytics here
    // For now, we'll just log them (already logged in component)
  };

  return (
    <html lang="en" className="h-full">
      <head>
        {/* Preload critical resources for performance */}
        <link
          rel="preload"
          href="/api/health"
          as="fetch"
          crossOrigin="anonymous"
        />

        {/* DNS prefetch for external resources */}
        <link rel="dns-prefetch" href="//fonts.googleapis.com" />
      </head>
      <body className={`${inter.className} font-sans h-full antialiased`}>
        <div className="h-full w-full">
          <PerformanceMonitor onMetricsUpdate={handleMetricsUpdate}>
            <AgentModeProvider>
              {children}
            </AgentModeProvider>
          </PerformanceMonitor>
        </div>
      </body>
    </html>
  );
}
