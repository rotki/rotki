import type { Ref, WritableComputedRef } from 'vue';

/**
 * The decimals an input holds, as the payload wants them.
 *
 * Anything that is not a whole number reads as "not set" rather than as a zero, so a half-typed or
 * cleared field never claims the token has no decimals.
 */
export function parseDecimals(value?: string): number | null {
  if (!value)
    return null;

  const parsed = Number.parseInt(value);
  return Number.isNaN(parsed) ? null : parsed;
}

/**
 * Binds a numeric decimals field to a text input.
 *
 * The input needs a string to write into and the payload needs a number, and the two disagree about
 * what empty means: the field shows nothing, the payload holds null. Interpolating the number
 * straight into a string is what put the word "null" in the managed asset form's decimals box.
 */
export function decimalsTextModel(
  decimals: Ref<number | null | undefined> | WritableComputedRef<number | null | undefined>,
  onChange?: () => void,
): WritableComputedRef<string> {
  return computed<string>({
    get: () => {
      const value = get(decimals);
      return value === null || value === undefined ? '' : `${value}`;
    },
    set: (value: string) => {
      set(decimals, parseDecimals(value));
      onChange?.();
    },
  });
}

/**
 * Binds an optional start timestamp to a date picker.
 *
 * The picker has no way to hold "no date", so an asset without one opens at the epoch, and clearing
 * it puts the epoch back rather than leaving the field undefined.
 */
export function startedEpochModel(
  started: Ref<number | null | undefined> | WritableComputedRef<number | null | undefined>,
): WritableComputedRef<number> {
  return computed<number>({
    get: () => get(started) ?? 0,
    set: (value?: number) => {
      set(started, value ?? 0);
    },
  });
}
