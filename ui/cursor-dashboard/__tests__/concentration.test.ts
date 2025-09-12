/**
 * Unit tests for computeHHIandCR4 concentration calculation utility
 * Tests HHI (Herfindahl-Hirschman Index) and CR4 (Concentration Ratio) calculations
 */

// Import the function from the main page component
// Note: In a real implementation, this would be extracted to a separate utility file
function computeHHIandCR4(sharesPct: (number | null | undefined)[]) {
  // Filter out null/undefined/NaN values
  const validShares = sharesPct.filter(s => 
    s !== null && s !== undefined && !isNaN(s)
  );
  
  // Need at least 2 valid shares to compute meaningful metrics
  if (validShares.length < 2) {
    return null;
  }
  
  // Round to integers (HHI rule: integer, no commas)
  const pctPts = validShares.map(s => Math.round(s as number));
  
  // HHI: sum of squared percentage points
  const hhi = pctPts.reduce((acc, p) => acc + p*p, 0);
  
  // CR4: sum of top 4 firms, rounded to nearest whole percent
  const cr4 = Math.round(
    [...pctPts].sort((a,b)=>b-a).slice(0,4).reduce((a,b)=>a+b,0)
  );
  
  return { hhi, cr4 };
}

describe('computeHHIandCR4', () => {
  describe('Standard test cases', () => {
    test('should compute HHI and CR4 for [21,21,26,16]', () => {
      const result = computeHHIandCR4([21, 21, 26, 16]);
      expect(result).toEqual({ hhi: 1814, cr4: 84 }); // 21^2 + 21^2 + 26^2 + 16^2 = 441 + 441 + 676 + 256 = 1814
    });

    test('should compute HHI and CR4 for [40,30,20,10]', () => {
      const result = computeHHIandCR4([40, 30, 20, 10]);
      expect(result).toEqual({ hhi: 3000, cr4: 100 });
    });

    test('should compute HHI and CR4 for [33.3,33.3,33.3] with rounding tolerance', () => {
      const result = computeHHIandCR4([33.3, 33.3, 33.3]);
      // 33.3 rounds to 33: 33^2 + 33^2 + 33^2 = 1089 + 1089 + 1089 = 3267
      // CR4: 33 + 33 + 33 = 99
      expect(result?.hhi).toBe(3267);
      expect(result?.cr4).toBe(99);
    });
  });

  describe('Edge cases and guardrails', () => {
    test('should return null when shares array has less than 2 valid values', () => {
      expect(computeHHIandCR4([21])).toBeNull();
      expect(computeHHIandCR4([])).toBeNull();
    });

    test('should return null when all shares are null/undefined/NaN', () => {
      expect(computeHHIandCR4([null, undefined, NaN])).toBeNull();
      expect(computeHHIandCR4([null, null])).toBeNull();
      expect(computeHHIandCR4([undefined, undefined])).toBeNull();
      expect(computeHHIandCR4([NaN, NaN])).toBeNull();
    });

    test('should filter out null/undefined/NaN and compute with valid shares', () => {
      const result = computeHHIandCR4([21, null, 26, undefined, 16, NaN]);
      expect(result).toEqual({ hhi: 1373, cr4: 63 }); // 21^2 + 26^2 + 16^2 = 441 + 676 + 256 = 1373, 26+21+16 = 63
    });

    test('should handle mixed valid and invalid values', () => {
      const result = computeHHIandCR4([40, null, 30, undefined, 20]);
      expect(result).toEqual({ hhi: 2900, cr4: 90 }); // 40^2 + 30^2 + 20^2 = 2900, 40+30+20 = 90
    });
  });

  describe('Rounding behavior', () => {
    test('should round HHI to integer (no decimals)', () => {
      const result = computeHHIandCR4([21.7, 21.3, 26.8, 16.2]);
      expect(Number.isInteger(result?.hhi)).toBe(true);
      expect(result?.hhi).toBe(1910); // 22^2 + 21^2 + 27^2 + 16^2 = 484 + 441 + 729 + 256 = 1910
    });

    test('should round CR4 to nearest whole percent', () => {
      const result = computeHHIandCR4([21.7, 21.3, 26.8, 16.2]);
      expect(Number.isInteger(result?.cr4)).toBe(true);
      expect(result?.cr4).toBe(86); // 27 + 22 + 21 + 16 = 86
    });
  });

  describe('CR4 calculation (top 4 firms)', () => {
    test('should sum top 4 firms even when more than 4 firms present', () => {
      const result = computeHHIandCR4([10, 20, 30, 40, 5, 15]);
      expect(result?.cr4).toBe(105); // Top 4: 40 + 30 + 20 + 15 = 105
    });

    test('should handle exactly 4 firms', () => {
      const result = computeHHIandCR4([25, 25, 25, 25]);
      expect(result?.cr4).toBe(100);
    });

    test('should handle less than 4 firms', () => {
      const result = computeHHIandCR4([50, 30, 20]);
      expect(result?.cr4).toBe(100); // 50 + 30 + 20 = 100
    });
  });
});
