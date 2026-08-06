import { omit } from 'es-toolkit';
import { z, type ZodType } from 'zod';
import { numberSettingField } from '@/modules/settings/controls/setting-field-schemas';
import { BalanceSource, type BalanceValueThreshold } from '@/modules/settings/types/frontend-settings';

export interface HideSmallBalancesFormState {
  hide: boolean;
  /** The threshold as typed; the setting stores it as a string too. */
  hideBelow: string;
  applyToAllBalances: boolean;
}

export interface HideSmallBalancesMessages {
  required: string;
  min: string;
}

export const DEFAULT_THRESHOLD = '1';

export function hideSmallBalancesSchema(messages: HideSmallBalancesMessages): ZodType {
  return z.object({
    applyToAllBalances: z.boolean(),
    hide: z.boolean(),
    hideBelow: numberSettingField({
      messages: { min: messages.min, required: messages.required },
      min: 0,
      required: true,
    }),
  });
}

/**
 * The thresholds as they should be stored. Hiding switched off clears this source (or all of them),
 * which the setting expresses by the key being absent rather than by a zero.
 */
export function toThresholds(
  state: HideSmallBalancesFormState,
  source: BalanceSource,
  current: BalanceValueThreshold,
): BalanceValueThreshold {
  const threshold = state.hide ? state.hideBelow : undefined;

  if (state.applyToAllBalances) {
    if (!threshold)
      return {};

    return {
      [BalanceSource.BLOCKCHAIN]: threshold,
      [BalanceSource.EXCHANGES]: threshold,
      [BalanceSource.MANUAL]: threshold,
    };
  }

  return {
    ...omit(current, [source]),
    ...(threshold ? { [source]: threshold } : {}),
  };
}
