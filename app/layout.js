import './globals.css';
import Link from 'next/link';

export const metadata = {
  title: 'Workout Tracker',
  description: 'Track your workouts and progress',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
  manifest: '/manifest.json',
  themeColor: '#007AFF',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Workout Tracker'
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-touch-fullscreen': 'yes'
  }
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
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  navigator.serviceWorker.register('/sw.js')
                    .then(registration => console.log('SW registered'))
                    .catch(error => console.log('SW registration failed'));
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
