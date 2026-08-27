import { assert, describe, expect, it } from 'vitest';
import {
  maxAmountFor,
  type ReminderRow,
  reminderRowsSchema,
  ReminderUnit,
  splitSeconds,
  toSeconds,
} from '@/modules/calendar/reminder-forms';

const HOUR = 60 * 60;
const DAY = HOUR * 24;

const messages = {
  amountMissing: 'missing',
  amountTooLarge: (max: number, unit: string): string => `max_${max}_${unit}`,
  amountTooSmall: 'too_small',
};

function parse(rows: ReminderRow[]): ReturnType<ReturnType<typeof reminderRowsSchema>['safeParse']> {
  return reminderRowsSchema(messages).safeParse({ rows });
}

function messagesFor(rows: ReminderRow[]): string[] {
  const result = parse(rows);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.message);
}

describe('splitSeconds', () => {
  it.each([
    [90 * 60, '90', ReminderUnit.MINUTES],
    [2 * HOUR, '2', ReminderUnit.HOURS],
    [3 * DAY, '3', ReminderUnit.DAYS],
    [2 * 7 * DAY, '2', ReminderUnit.WEEKS],
    [900, '15', ReminderUnit.MINUTES],
  ])('should split %i seconds into the largest unit that divides it evenly', (seconds, amount, unit) => {
    expect(splitSeconds(seconds)).toEqual({ amount, unit });
  });

  it('should fall back to whole minutes when nothing divides evenly', () => {
    expect(splitSeconds(90)).toEqual({ amount: '1', unit: ReminderUnit.MINUTES });
  });

  it('should round trip through seconds', () => {
    expect(toSeconds(splitSeconds(3 * DAY))).toBe(3 * DAY);
  });
});

describe('maxAmountFor', () => {
  it.each([
    [ReminderUnit.MINUTES, 43200],
    [ReminderUnit.HOURS, 720],
    [ReminderUnit.DAYS, 30],
    [ReminderUnit.WEEKS, 4],
  ])('should cap %s at %i', (unit, expected) => {
    expect(maxAmountFor(unit)).toBe(expected);
  });
});

describe('reminderRowsSchema', () => {
  it('should accept a row inside its range', () => {
    expect(parse([{ amount: '3', unit: ReminderUnit.HOURS }]).success).toBe(true);
  });

  it('should accept no rows at all', () => {
    expect(parse([]).success).toBe(true);
  });

  it('should reject an empty amount', () => {
    expect(messagesFor([{ amount: '', unit: ReminderUnit.HOURS }])).toEqual(['missing']);
  });

  it('should reject a zero amount', () => {
    expect(messagesFor([{ amount: '0', unit: ReminderUnit.HOURS }])).toEqual(['too_small']);
  });

  it('should reject an amount above the ceiling for its unit, which moves with the unit', () => {
    expect(messagesFor([{ amount: '5', unit: ReminderUnit.WEEKS }])).toEqual(['max_4_weeks']);
    expect(parse([{ amount: '5', unit: ReminderUnit.HOURS }]).success).toBe(true);
  });

  it('should report only one message per row', () => {
    expect(messagesFor([{ amount: '', unit: ReminderUnit.HOURS }])).toHaveLength(1);
  });

  it('should key a message to the row it came from, rows being addressed by index', () => {
    const result = parse([
      { amount: '2', unit: ReminderUnit.HOURS },
      { amount: '99999', unit: ReminderUnit.WEEKS },
    ]);

    assert(!result.success);
    expect(result.error.issues[0].path).toEqual(['rows', 1, 'amount']);
  });
});
