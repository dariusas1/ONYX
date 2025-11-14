/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // !! WARN !!
    // Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    // !! WARN !!
    ignoreBuildErrors: true,
  },
  // Font Optimization Configuration:
  // For offline/CI builds without network access, set NEXT_PUBLIC_SKIP_FONTS=true
  // This will use system fonts instead of downloading from Google Fonts
  // Example: NEXT_PUBLIC_SKIP_FONTS=true npm run build
}

module.exports = nextConfig