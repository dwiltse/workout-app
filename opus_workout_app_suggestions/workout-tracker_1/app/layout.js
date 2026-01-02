import './globals.css';
import Link from 'next/link';

export const metadata = {
  title: 'Workout Tracker',
  description: 'Track your workouts and progress',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
        <nav className="nav">
          <Link href="/" className="nav-item">
            <span>🏠</span>
            <span>Home</span>
          </Link>
          <Link href="/routines" className="nav-item">
            <span>📋</span>
            <span>Routines</span>
          </Link>
          <Link href="/history" className="nav-item">
            <span>📊</span>
            <span>History</span>
          </Link>
          <Link href="/weight" className="nav-item">
            <span>⚖️</span>
            <span>Weight</span>
          </Link>
        </nav>
      </body>
    </html>
  );
}
