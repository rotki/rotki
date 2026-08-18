import { describe, expect, it, vi } from 'vitest';
import { DateFormat } from '@/modules/core/common/date-format';
import { usePillSyntaxHints } from '@/modules/core/table/pill/composables/use-pill-syntax-hints';

const dateInputFormat = ref<DateFormat>(DateFormat.DateMonthYearHourMinuteSecond);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'dateInputFormat' ? dateInputFormat : ref(undefined))),
}));

describe('usePillSyntaxHints', () => {
  // Asserted whole, not by substring: the formatter appends a time of day to any timestamp that is
  // not on local midnight, and an example reading `after 15/01/2024 14:00` teaches a syntax nobody
  // asked for. A `toContain` check passes straight through that.
  const dates = (): readonly string[] => get(usePillSyntaxHints()).examples?.date ?? [];

  // The example exists to state the field order, so writing it in a fixed order would teach the
  // wrong one to everybody whose format is not that order.
  it('should write the date examples in the user configured format', () => {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 15/01/2024', 'before 15/01/2024', '15/01/2024 - 20/01/2024']);

    set(dateInputFormat, DateFormat.MonthDateYearHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 01/15/2024', 'before 01/15/2024', '01/15/2024 - 01/20/2024']);

    set(dateInputFormat, DateFormat.YearMonthDateHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 2024/01/15', 'before 2024/01/15', '2024/01/15 - 2024/01/20']);
  });

  // The operator words and the span separator are what the parser knows, in English. Translating
  // them would hand the user an example the bar then refuses, so they are never passed through `t`.
  // This is also why `before` needs its own chip: the bare-date rows that would otherwise show the
  // word are labelled with the *translated* operator, which is not what the parser accepts.
  it('should keep the operator words literal', () => {
    expect(dates()[0]).toMatch(/^after /);
    expect(dates()[1]).toMatch(/^before /);
    expect(dates()[2]).toContain(' - ');
  });

  // A day inside the first twelve would read as the month to half the world, which is the one
  // thing the example is there to settle.
  it('should use a day past the twelfth so the order cannot be misread', () => {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
    const [day] = dates()[0].replace('after ', '').split('/');
    expect(Number(day)).toBeGreaterThan(12);
  });

  it('should follow the format when it changes under an existing hint', () => {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
    const hints = usePillSyntaxHints();
    expect(get(hints).examples?.date?.[0]).toBe('after 15/01/2024');

    set(dateInputFormat, DateFormat.MonthDateYearHourMinuteSecond);
    expect(get(hints).examples?.date?.[0]).toBe('after 01/15/2024');
  });

  // The span separator has to be spaced or `DATE_SPAN` will not split it, so an example copied
  // out of the footer has to carry the spaces it needs.
  it('should space the span separator so the example parses when copied', () => {
    expect(dates()[2]).toMatch(/\d - \d/);
  });

  it('should offer keywords for the two typed-into value types', () => {
    const hints = get(usePillSyntaxHints());
    expect(hints.keywords?.date).toBeDefined();
    expect(hints.keywords?.range).toBeDefined();
  });

  // One chip per shape, both types alike: a lower bound, an upper bound, a span. A single-direction
  // chip reads as though that is the only direction the bar takes.
  it('should cover both bounds and the span for an amount', () => {
    expect(get(usePillSyntaxHints()).examples?.range).toStrictEqual(['>100', '<10', '10 - 50']);
  });

  it('should cover both bounds and the span for a date', () => {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 15/01/2024', 'before 15/01/2024', '15/01/2024 - 20/01/2024']);
  });
});
