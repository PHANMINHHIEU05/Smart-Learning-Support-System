/** @type {import('next').NextConfig} */

const isDevelopment = process.env.NODE_ENV !== "production";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-XSS-Protection", value: "1; mode=block" },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      `script-src 'self'${isDevelopment ? " 'unsafe-inline' 'unsafe-eval'" : ""}`,
      "style-src 'self' 'unsafe-inline'", // Tailwind requires inline styles in dev
      "img-src 'self' data: blob:",
      "font-src 'self'",
      `connect-src 'self' https://*.supabase.co wss://*.supabase.co http://localhost:8000 http://localhost:8080${isDevelopment ? " ws://localhost:3000 ws://localhost:3001 ws://localhost:3002" : ""}`,
      "frame-ancestors 'none'",
    ].join("; "),
  },
];

const nextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
