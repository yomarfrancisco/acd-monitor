import { test, expect } from "@playwright/test";

/**
 * Dashboard CTA Button Styling Tests
 * 
 * Tests that verify the computed styles of Dashboard CTA buttons match
 * the expected design specifications. This prevents style regressions
 * and ensures visual consistency across all CTA buttons.
 */

// Convert hex color to RGB for computed style comparison
const rgb = (hex: string) => {
  const h = hex.replace("#", "");
  const n = (i: number) => parseInt(h.slice(i, i + 2), 16);
  return `rgb(${n(0)}, ${n(2)}, ${n(4)})`;
};

// Expected colors from design spec
const EXPECTED_BG = rgb("#AFC8FF"); // Pastel blue background
const EXPECTED_TEXT = "rgb(0, 0, 0)"; // Black text

test.describe("Dashboard CTA Button Styling", () => {
  test("CTAs have correct background and text color", async ({ page }) => {
    // Navigate to the app
    await page.goto("/");
    
    // Switch to Dashboard tab
    await page.getByRole("button", { name: "Dashboard" }).click();

    // Define the CTA button labels we expect to find
    const ctaLabels = [
      "Connect", 
      "Invite Your Team", 
      "Deploy",
      "Download"
    ];

    // Test each CTA button type
    for (const label of ctaLabels) {
      const buttons = page.getByRole("button", { name: label });
      const count = await buttons.count();
      
      // Verify we found at least one button of this type
      expect(count).toBeGreaterThan(0);
      
      // Test each instance of this button type
      for (let i = 0; i < count; i++) {
        const button = buttons.nth(i);
        
        // Ensure button is visible in viewport
        await button.scrollIntoViewIfNeeded();
        
        // Get computed styles
        const bgColor = await button.evaluate(el => 
          getComputedStyle(el as HTMLElement).backgroundColor
        );
        const textColor = await button.evaluate(el => 
          getComputedStyle(el as HTMLElement).color
        );

        // Assert background color matches expected pastel blue
        expect(bgColor).toBe(EXPECTED_BG);
        
        // Assert text color is black
        expect(textColor).toBe(EXPECTED_TEXT);
      }
    }
  });

  test("CTA buttons maintain consistent styling across sections", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Dashboard" }).click();

    // Test a few specific CTAs to ensure they're consistent
    const testButtons = [
      { name: "Connect", expectedCount: 5 }, // Overview + 4 Data Sources
      { name: "Deploy", expectedCount: 4 },  // 4 AI Agents
      { name: "Download", expectedCount: 3 } // 3 Compliance Reports
    ];

    for (const { name, expectedCount } of testButtons) {
      const buttons = page.getByRole("button", { name });
      const count = await buttons.count();
      
      // Verify we have the expected number of buttons
      expect(count).toBe(expectedCount);
      
      // Test first button to ensure styling is consistent
      if (count > 0) {
        const firstButton = buttons.first();
        await firstButton.scrollIntoViewIfNeeded();
        
        const bgColor = await firstButton.evaluate(el => 
          getComputedStyle(el as HTMLElement).backgroundColor
        );
        const textColor = await firstButton.evaluate(el => 
          getComputedStyle(el as HTMLElement).color
        );

        expect(bgColor).toBe(EXPECTED_BG);
        expect(textColor).toBe(EXPECTED_TEXT);
      }
    }
  });
});
