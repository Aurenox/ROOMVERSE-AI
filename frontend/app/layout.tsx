import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = {
  title: "ROOMVERSE AI | Open a case",
  description: "Observe the evidence, find the connection, and close the case.",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
