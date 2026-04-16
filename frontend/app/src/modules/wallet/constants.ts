import type { GasFeeEstimation } from '@/modules/wallet/types';

/**
 * Wallet mode constants
 */
export const WALLET_MODES = {
  LOCAL_BRIDGE: 'local-bridge',
  WALLET_CONNECT: 'walletconnect',
} as const;

export type WalletMode = typeof WALLET_MODES[keyof typeof WALLET_MODES];

export const EIP155 = 'eip155';

export const SUPPORTED_WALLET_CHAIN_IDS = [1, 8453, 42161, 10, 56, 100, 137, 534352] as const;

/**
 * Transaction constants
 */
const DEFAULT_GAS_LIMIT = 21000n;

/**
 * Error messages
 */
export const WALLET_ERRORS = {
  CONNECTION_FAILED: 'Failed to initiate wallet connection',
  GAS_ESTIMATION_FAILED: 'Error getting gas fee',
  NO_PROVIDERS: 'No wallet providers detected',
} as const;

/**
 * Keywords that indicate a user rejected a wallet action
 */
const REJECTED_KEYWORDS = [
  'ACTION_REJECTED',
  'User cancelled',
  'User canceled',
  'User rejected',
] as const;

/**
 * Check if an error indicates user rejection
 */
export function isUserRejectedError(error: Error | unknown): boolean {
  const errorString = error instanceof Error ? error.toString() : String(error);
  return REJECTED_KEYWORDS.some(keyword => errorString.includes(keyword));
}

/**
 * Buffer percentages
 */
const GAS_PRICE_BUFFER_PERCENTAGE = 10n;

/**
 * Utility functions
 */

/**
 * Format wei (18 decimals) to a decimal string using pure bigint arithmetic.
 * Replaces ethers `formatUnits` to avoid importing ethers in this constants file.
 */
function formatWei(value: bigint): string {
  const DIVISOR = 10n ** 18n;
  const integerPart = value / DIVISOR;
  const remainder = value % DIVISOR;
  if (remainder === 0n)
    return integerPart.toString();
  const fractionalPart = remainder.toString().padStart(18, '0').replace(/0+$/, '');
  return `${integerPart}.${fractionalPart}`;
}

/**
 * Calculate gas fee estimation based on fee data and balance
 */
export function calculateGasFee(gasPrice: bigint, balance: bigint): GasFeeEstimation {
  let maxAmount = '0';
  let gasFee = '0';

  const gasCost = gasPrice * DEFAULT_GAS_LIMIT;

  if (balance > gasCost) {
    // Add buffer for gas price fluctuations
    const buffer = gasCost * GAS_PRICE_BUFFER_PERCENTAGE / 100n;
    const diff = gasCost + buffer;

    const maxSendable = balance - diff;
    gasFee = formatWei(diff);
    maxAmount = formatWei(maxSendable);
  }

  return {
    gasFee,
    maxAmount,
  };
}
