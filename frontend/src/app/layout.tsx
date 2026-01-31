import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'OpMech-GraphRAG | Multi-Perspective Knowledge Retrieval',
  description:
    'A groundbreaking approach to knowledge retrieval through quantum-inspired operator mechanics. Dual-operator traversal meets intelligent mode selection.',
  keywords: [
    'GraphRAG',
    'Knowledge Graph',
    'AI',
    'Machine Learning',
    'SEC Filings',
    'Financial Analysis',
  ],
  authors: [{ name: 'SP Jain School of Global Management' }],
  openGraph: {
    title: 'OpMech-GraphRAG',
    description: 'Multi-Perspective Knowledge Retrieval Through Quantum-Inspired Operator Mechanics',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
