import z from 'zod';
import { NumericString } from '../numbers';

/**
 * Mirrors the backend's `Balance.serialize()`, which always emits both fields. `value` used to
 * default to zero when absent, which turned a schema that did not match its endpoint into a silent
 * zero instead of a parse error, and hid the same bug twice (#11766, #12822). A missing `value` now
 * fails loudly: an endpoint that sends something else needs its own schema, not this one.
 */
export const Balance = z.object({
  amount: NumericString,
  value: NumericString,
});

export type Balance = z.infer<typeof Balance>;

export const AssetEntry = z.object({
  asset: z.string().min(1),
});

export const AssetBalance = z.object({
  ...Balance.shape,
  ...AssetEntry.shape,
});

export type AssetBalance = z.infer<typeof AssetBalance>;

export const Percentage = z.string().refine((arg) => {
  const number = Number.parseFloat(arg);
  return Number.isFinite(number) && number >= 0 && number <= 100;
}, {
  message: 'Percentage must be between 0 and 100',
});

/** An account holding a position that has to be claimed by the user. */
export interface ClaimAccount {
  address: string;
  chain: string;
}

/**
 * A withdrawal request that waits for its owner to claim it.
 *
 * @remarks
 * Timestamps are in seconds. Whether it is ready is not stored: it is if `finalized`, or once
 * `availableAt` has passed.
 */
export interface ClaimRequest {
  amount: Balance['amount'];
  /** Where the request sits, filled in when the balances of the accounts are combined. */
  account?: ClaimAccount;
  availableAt?: number;
  finalized: boolean;
  id?: string;
  requestedAt?: number;
}

export type ProtocolBalance = Balance & {
  awaitingClaim?: Balance['amount'];
  claims?: ClaimRequest[];
  containsManual?: boolean;
  protocol: string;
};

export type ProtocolBalanceWithChains = ProtocolBalance & { chains?: Record<string, Balance> };

type Breakdown = AssetBalance & { price: Balance['value']; perProtocol?: ProtocolBalance[] };

export type AssetBalanceWithPrice = Breakdown & { breakdown?: Breakdown[] };

export type AssetBalanceWithPriceAndChains = Omit<AssetBalanceWithPrice, 'perProtocol'> & {
  perProtocol?: ProtocolBalanceWithChains[];
};
