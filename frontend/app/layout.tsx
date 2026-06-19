import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Providers from "@/components/Providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "VidyamargAI — AI-Powered Career & Learning Platform",
    template: "%s | VidyamargAI",
  },
  description:
    "VidyamargAI is an AI-powered platform for smart job matching, skill-lab courses, mock interviews, and resume building — built for the next generation of Indian tech talent.",
  keywords: [
    "AI jobs India",
    "skill lab",
    "mock interview",
    "resume builder",
    "career platform",
    "VidyamargAI",
  ],
  authors: [{ name: "VidyamargAI Team" }],
  creator: "VidyamargAI",
  metadataBase: new URL("https://vidyamargai-production.up.railway.app"),
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://vidyamargai-production.up.railway.app",
    siteName: "VidyamargAI",
    title: "VidyamargAI — AI-Powered Career & Learning Platform",
    description:
      "Smart job matching, skill-lab LMS, AI mock interviews, and resume analysis — all in one platform.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "VidyamargAI Platform Preview",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "VidyamargAI — AI-Powered Career & Learning Platform",
    description:
      "Smart job matching, skill-lab LMS, AI mock interviews, and resume analysis — all in one platform.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F5F5F5" },
    { media: "(prefers-color-scheme: dark)", color: "#0A0A0A" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://www.youtube.com" />
        <link rel="preconnect" href="https://s.ytimg.com" />
        <link rel="preconnect" href="https://i.ytimg.com" />
        <script src="https://www.youtube.com/iframe_api" async></script>
      </head>
      <body className="min-h-full flex flex-col">
        {/* Inline theme script — runs before paint to prevent flash of wrong theme */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme')||'system';var d=false;if(t==='system'){d=window.matchMedia('(prefers-color-scheme: dark)').matches;}else{d=(t==='dark');}if(d){document.documentElement.classList.add('dark');document.documentElement.classList.remove('light-theme');}else{document.documentElement.classList.remove('dark');document.documentElement.classList.add('light-theme');}}catch(e){}})()`,
          }}
        />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
