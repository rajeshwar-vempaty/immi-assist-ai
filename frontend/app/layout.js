export const metadata = {
  title: "ImmiAssist AI — Your Immigration Assistant",
  description:
    "AI-powered immigration guidance platform. Get instant answers about US visas, green cards, and immigration processes.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  );
}
