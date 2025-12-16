/**
 * E2E Test Constants
 *
 * Centralized constants for timeout values, viewport configurations,
 * and other shared test values.
 */

// Timeout constants (in milliseconds)
export const TIMEOUT_SHORT = 5000;

export const TIMEOUT_MEDIUM = 10000;

export const TIMEOUT_DIALOG = 45000;

export const TIMEOUT_LONG = 120000;

/** Extended timeout for operations like blockchain balance fetching */
export const TIMEOUT_VERY_LONG = 300000;

// Test timeout for spec files
export const TEST_TIMEOUT_STANDARD = 120000;

export const TEST_TIMEOUT_BLOCKCHAIN = 180000;

// Comparison precision for balance assertions
export const BALANCE_PRECISION = 0.1;

// Viewport configurations for responsive testing
export const VIEWPORTS = [
  { width: 1280, height: 720, name: 'HD Ready' },
  { width: 1000, height: 660, name: 'Default viewport' },
  { width: 800, height: 600, name: 'Rotki minimum supported resolution' },
  { width: 640, height: 480, name: 'Small res to simulate high app scaling or zoom' },
] as const;
