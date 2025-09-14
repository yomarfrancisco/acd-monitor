import type React from "react";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div data-probe="dash-layout" style={{outline:'3px solid lime', padding:4}}>
      <aside data-probe="dash-sidenav-mount" />
      <main>{children}</main>
    </div>
  );
}