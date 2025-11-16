import type { Metadata } from 'next';
import '@/styles/globals.css';
import { ModeProvider } from '@/contexts/ModeContext';

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
      <body className={`${inter.className} font-sans`}>
        <ModeProvider>
          {children}
        </ModeProvider>
      </body>
    </html>
  );
}
