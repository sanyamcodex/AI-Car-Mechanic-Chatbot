import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Car Mechanic Chatbot',
  description: 'Virtual senior mechanic chatbot for vehicle troubleshooting, diagnosis, and repair booking.',
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🔧</text></svg>',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
