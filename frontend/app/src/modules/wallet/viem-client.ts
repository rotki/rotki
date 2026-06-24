import type { EIP1193Provider } from '@/types';
import { BaseError, createWalletClient, custom, type CustomTransport, type PublicActions, publicActions, UserRejectedRequestError, type WalletClient } from 'viem';

/**
 * Single entry point for viem in the wallet stack. The rest of the wallet
 * modules import the primitives they need (`getAddress`, `isHex`, the `Hash`/
 * `Hex`/`Address` types) from here rather than from `viem` directly, so the
 * dependency surface stays in one file.
 */
export { getAddress, isHex } from 'viem';

export type { Address, Chain, Hash, Hex } from 'viem';

export type ViemWalletClient = WalletClient<CustomTransport, undefined, undefined>
  & PublicActions<CustomTransport, undefined, undefined>;

/**
 * Builds a viem wallet client backed by an EIP-1193 provider and extends it
 * with public actions, so a single client can both sign/send transactions and
 * perform reads (gas price, balances, receipt waiting) over the same transport.
 *
 * Both wallet backends (injected bridge and WalletConnect) expose the resulting
 * client through `getWalletClient()`, replacing the previous ethers
 * `BrowserProvider` seam.
 */
export function createViemWalletClient(provider: EIP1193Provider): ViemWalletClient {
  return createWalletClient({ transport: custom(provider) }).extend(publicActions);
}

/**
 * EIP-1193 error code emitted when the user rejects a wallet request.
 */
const USER_REJECTION_CODE = 4001;

function hasRejectionCode(error: unknown): boolean {
  return (
    typeof error === 'object'
    && error !== null
    && 'code' in error
    && error.code === USER_REJECTION_CODE
  );
}

/**
 * Detects whether an error means the user rejected the wallet request.
 *
 * viem wraps provider errors in a `BaseError` chain, so we walk that chain for
 * either viem's typed `UserRejectedRequestError` or the raw EIP-1193 `4001`
 * code. Some wallets (e.g. MetaMask) surface the rejection as a generic
 * "unknown RPC error" whose original `4001` only survives in the cause chain,
 * which plain message matching used to miss.
 */
export function isUserRejectedRequestError(error: unknown): boolean {
  if (error instanceof BaseError) {
    const matched = error.walk(inner =>
      inner instanceof UserRejectedRequestError || hasRejectionCode(inner),
    );
    if (matched)
      return true;
  }
  return hasRejectionCode(error);
}

/**
 * Extracts a concise, user-facing message from a viem error.
 *
 * viem's `BaseError.message` is a verbose multi-line block (request arguments,
 * a docs link and a `Version: viem@x` footer) meant for developers. For display
 * we prefer the provider's own `details` line (most specific, e.g. the wallet's
 * own wording) and fall back to viem's one-line `shortMessage`. Returns
 * `undefined` for non-viem errors so callers can apply their own fallback.
 */
export function getViemErrorMessage(error: unknown): string | undefined {
  if (error instanceof BaseError)
    return error.details || error.shortMessage || error.message;
  return undefined;
}
