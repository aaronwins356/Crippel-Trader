import Providers from './providers';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Crypto Research Dashboard',
  description: 'Professional-grade crypto asset tracking and comparison',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}