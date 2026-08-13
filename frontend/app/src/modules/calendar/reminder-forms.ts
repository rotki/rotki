import { z, type ZodType } from 'zod';

export const ReminderUnit = {
  DAYS: 'days',
  HOURS: 'hours',
  MINUTES: 'minutes',
  WEEKS: 'weeks',
} as const;

export type ReminderUnit = typeof ReminderUnit[keyof typeof ReminderUnit];

/** Smallest first: this is the order the unit selector offers them in. */
export const REMINDER_UNITS: readonly ReminderUnit[] = [
  ReminderUnit.MINUTES,
  ReminderUnit.HOURS,
  ReminderUnit.DAYS,
  ReminderUnit.WEEKS,
];

const SECONDS: Record<ReminderUnit, number> = {
  [ReminderUnit.MINUTES]: 60,
  [ReminderUnit.HOURS]: 60 * 60,
  [ReminderUnit.DAYS]: 60 * 60 * 24,
  [ReminderUnit.WEEKS]: 60 * 60 * 24 * 7,
};

/** A reminder may be set at most thirty days before its event. */
export const MAX_SECONDS_BEFORE = 60 * 60 * 24 * 30;

export function secondsIn(unit: ReminderUnit): number {
  return SECONDS[unit];
}

/** The largest whole amount of `unit` that stays within the thirty-day ceiling. */
export function maxAmountFor(unit: ReminderUnit): number {
  return Math.floor(MAX_SECONDS_BEFORE / secondsIn(unit));
}

export interface ReminderRow {
  /** Held as typed, so a half-written or out-of-range entry is representable rather than dropped. */
  amount: string;
  unit: ReminderUnit;
}

/**
 * Splits an interval into the largest unit that divides it evenly, so ninety minutes stays ninety
 * minutes rather than becoming an hour and a half.
 */
export function splitSeconds(seconds: number): ReminderRow {
  for (const unit of [...REMINDER_UNITS].reverse()) {
    const amount = seconds / secondsIn(unit);
    if (Number.isInteger(amount))
      return { amount: amount.toString(), unit };
  }

  return { amount: Math.floor(seconds / 60).toString(), unit: ReminderUnit.MINUTES };
}

export function toSeconds(row: ReminderRow): number {
  return Number(row.amount) * secondsIn(row.unit);
}

export interface ReminderMessages {
  amountMissing: string;
  amountTooLarge: (max: number, unit: ReminderUnit) => string;
  amountTooSmall: string;
}

export interface ReminderRowsState {
  rows: ReminderRow[];
}

/**
 * The ceiling depends on the unit the row is set to, so it is checked per row rather than by a rule
 * on the amount alone.
 */
export function reminderRowsSchema(messages: ReminderMessages): ZodType {
  const row = z.object({
    amount: z.string(),
    unit: z.enum(REMINDER_UNITS),
  }).superRefine((value, ctx) => {
    if (value.amount.trim() === '') {
      ctx.addIssue({ code: 'custom', message: messages.amountMissing, path: ['amount'] });
      return;
    }

    const amount = Number(value.amount);
    if (!Number.isFinite(amount) || amount < 1) {
      ctx.addIssue({ code: 'custom', message: messages.amountTooSmall, path: ['amount'] });
      return;
    }

    const max = maxAmountFor(value.unit);
    if (amount > max)
      ctx.addIssue({ code: 'custom', message: messages.amountTooLarge(max, value.unit), path: ['amount'] });
  });

  return z.object({ rows: z.array(row) });
}
