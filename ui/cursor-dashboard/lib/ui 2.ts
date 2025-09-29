/**
 * UI Constants - Dashboard CTA Button Styling
 * 
 * Centralized styling constants to prevent style drift and ensure consistency
 * across Dashboard CTA buttons. Any changes to these styles should be
 * coordinated and tested to maintain visual consistency.
 */

/**
 * Dashboard CTA Button Class
 * 
 * Standard styling for all Dashboard CTA buttons (Connect, Deploy, Download, etc.)
 * - Background: Pastel blue (#AFC8FF)
 * - Hover: Darker blue (#9FBCFF) 
 * - Text: Black
 * - Size: Small (9px, h-5, px-2)
 * 
 * Used by: Overview, Data Sources, AI Agents, Compliance Reports sections
 * Excludes: "Manage Subscription" and "Edit Limit" buttons
 */
export const dashboardCtaBtnClass =
  "border-[#AFC8FF] text-black bg-[#AFC8FF] hover:bg-[#9FBCFF] text-[9px] h-5 px-2 font-normal";

/**
 * Dashboard Layout Tokens
 * 
 * Responsive layout utilities for dashboard pages following Cursor pattern:
 * - Mobile: single column with nav-first layout
 * - Desktop: grid layout with sticky sidebar
 */
export const dashContainer = "mx-auto max-w-[1120px] px-3 sm:px-4 lg:px-6";
export const dashGrid = "grid gap-6 lg:grid-cols-[18rem_1fr]";
export const sectionTitle = "text-lg font-medium tracking-tight";
export const card = "rounded-xl border border-white/10 bg-white/5 p-4 md:p-6";
export const navList = "flex flex-col gap-1";
export const navItem = "flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-white/5";
export const navItemActive = "bg-white/10";

/**
 * Class concatenation helper
 * 
 * Utility function to safely concatenate CSS classes, filtering out
 * falsy values (false, null, undefined, empty strings)
 */
export const cx = (...s: (string | false | null | undefined)[]) => 
  s.filter(Boolean).join(" ");
