import type { BalanceType } from '@/modules/balances/types/balances';
import { z, type ZodType } from 'zod';

/**
 * A field that must hold something. Vuelidate's `required` treated a whitespace-only string as
 * empty and reported a missing value under the same message as a wrong-typed one, so both are kept.
 */
function requiredField(message: string): ZodType<string> {
  return z.string({ error: message }).superRefine((value, ctx) => {
    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message });
  });
}

export interface LocationDataSnapshotFormState {
  location: string;
  timestamp: number;
  usdValue: string;
}

export interface LocationDataSnapshotMessages {
  location: string;
  value: string;
}

export function locationDataSnapshotSchema(messages: LocationDataSnapshotMessages): ZodType {
  return z.object({
    location: requiredField(messages.location),
    timestamp: z.number(),
    usdValue: requiredField(messages.value),
  });
}

export interface BalanceSnapshotFormState {
  amount: string;
  assetIdentifier: string;
  category: BalanceType;
  location: string;
  timestamp: number;
  usdValue: string;
}

export interface BalanceSnapshotMessages {
  category: string;
  location: string;
  locationInsufficient: string;
}

export interface BalanceSnapshotRules {
  /** Location ids that cannot absorb the edited value. */
  disabledLocations: readonly string[];
  /** While the single-location selector is hidden, the caller drives attribution itself. */
  hideLocation: boolean;
  messages: BalanceSnapshotMessages;
}

/**
 * The balance form gates on the category and the location alone. The asset, amount and value are
 * carried so the form owns one state, but they are validated by the price sub-form, whose messages
 * are for display only - see `assetPriceSchema`.
 */
export function balanceSnapshotSchema(rules: BalanceSnapshotRules): ZodType {
  const { disabledLocations, hideLocation, messages } = rules;

  return z.object({
    amount: z.string(),
    assetIdentifier: z.string(),
    category: requiredField(messages.category),
    location: z.string(),
    timestamp: z.number(),
    usdValue: z.string(),
  }).superRefine((state, ctx) => {
    // Required whenever the selector is shown: every balance must be attributed so the location
    // subtotals reconcile with the net worth. In split mode the split drives attribution instead.
    if (!hideLocation && state.location.trim() === '')
      ctx.addIssue({ code: 'custom', message: messages.location, path: ['location'] });

    // Checked even in split mode, matching the rule it replaces.
    if (state.location !== '' && disabledLocations.includes(state.location))
      ctx.addIssue({ code: 'custom', message: messages.locationInsufficient, path: ['location'] });
  });
}

export interface AssetPriceFormState {
  amount: string;
  asset: string;
  usdValue: string;
}

export interface AssetPriceMessages {
  amount: string;
  asset: string;
  value: string;
}

/**
 * Display-only rules for the price sub-form. That form exposes no `validate`, so nothing here can
 * block a save; it decorates the fields while `balanceSnapshotSchema` holds the actual gate.
 */
export function assetPriceSchema(messages: AssetPriceMessages): ZodType {
  return z.object({
    amount: requiredField(messages.amount),
    asset: requiredField(messages.asset),
    usdValue: requiredField(messages.value),
  });
}
