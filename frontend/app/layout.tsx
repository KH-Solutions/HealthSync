import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
    variable: "--font-geist-sans",
    subsets: ["latin"],
});

const geistMono = Geist_Mono({
    variable: "--font-geist-mono",
    subsets: ["latin"],
});

export const metadata: Metadata = {
    title: "Health Sync - Twoje Centrum Zdrowia",
    description: "Synchronizuj, analizuj i zarządzaj swoimi danymi zdrowotnymi z różnych aplikacji w jednym, bezpiecznym miejscu.",
    keywords: ["zdrowie", "fitness", "synchronizacja danych", "Google Fit", "Apple Health", "Garmin", "analiza zdrowia"],
    authors: [{ name: "KH Solutions", url: "https://github.com/KH-Solutions" }],
    robots: {
        index: true,
        follow: true,
    },

    openGraph: {
        title: "Health Sync - Zintegruj Swoje Dane o Zdrowiu",
        description: "Połącz wszystkie swoje aplikacje zdrowotne i zyskaj pełen obraz swojej kondycji.",
        type: "website",
        url: "https://health-sync.com",
        siteName: "Health Sync",
        // You can add the URL of the image that will be displayed when sharing the link
        // images: [
        //   {
        //     url: "https://health-sync.com/og-image.png",
        //     width: 1200,
        //     height: 630,
        //     alt: "Health Sync logo on a dashboard background",
        //   },
        // ],
    },
};


export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="pl">
            <body
                className={`${geistSans.variable} ${geistMono.variable} antialiased`}
            >
                {children}
            </body>
        </html>
    );
}