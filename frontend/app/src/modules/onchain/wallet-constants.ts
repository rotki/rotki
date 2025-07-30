import type { GasFeeEstimation } from '@/modules/onchain/types';
import { formatUnits } from 'ethers';

/**
 * Wallet mode constants
 */
export const WALLET_MODES = {
  LOCAL_BRIDGE: 'local-bridge',
  WALLET_CONNECT: 'walletconnect',
} as const;

export type WalletMode = typeof WALLET_MODES[keyof typeof WALLET_MODES];

/**
 * Transaction constants
 */
export const DEFAULT_GAS_LIMIT = 21000n;

/**
 * Error messages
 */
export const WALLET_ERRORS = {
  CONNECTION_FAILED: 'Failed to initiate wallet connection',
  GAS_ESTIMATION_FAILED: 'Error getting gas fee',
  NO_PROVIDERS: 'No wallet providers detected',
} as const;

/**
 * Buffer percentages
 */
export const GAS_PRICE_BUFFER_PERCENTAGE = 10n;

/**
 * Utility functions
 */

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
    gasFee = formatUnits(diff);
    maxAmount = formatUnits(maxSendable, 18);
  }

  return {
    gasFee,
    maxAmount,
  };
}
