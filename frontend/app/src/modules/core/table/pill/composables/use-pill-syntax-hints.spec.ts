import { describe, expect, it, vi } from 'vitest';
import { DateFormat } from '@/modules/core/common/date-format';
import { usePillSyntaxHints } from '@/modules/core/table/pill/composables/use-pill-syntax-hints';

const dateInputFormat = ref<DateFormat>(DateFormat.DateMonthYearHourMinuteSecond);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'dateInputFormat' ? dateInputFormat : ref(undefined))),
}));

const TIME_OF_DAY = /\d{1,2}:\d{2}/;

describe('usePillSyntaxHints', () => {
  function dates(): readonly string[] {
    const examples = get(usePillSyntaxHints()).examples?.date ?? [];
    for (const example of examples)
      expect(example).not.toMatch(TIME_OF_DAY);
    return examples;
  }

  it('should write the date examples in the user configured format', () => {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 15/01/2024', 'before 15/01/2024', '15/01/2024 - 20/01/2024']);

    set(dateInputFormat, DateFormat.MonthDateYearHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 01/15/2024', 'before 01/15/2024', '01/15/2024 - 01/20/2024']);

    set(dateInputFormat, DateFormat.YearMonthDateHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 2024/01/15', 'before 2024/01/15', '2024/01/15 - 2024/01/20']);
  });

  it('should keep the operator words untranslated so the parser still accepts the example', () => {
    expect(dates()[0]).toMatch(/^after /);
    expect(dates()[1]).toMatch(/^before /);
    expect(dates()[2]).toContain(' - ');
  });

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

  it('should space the span separator so the example parses when copied', () => {
    expect(dates()[2]).toMatch(/\d - \d/);
  });

  it('should offer keywords for the two typed-into value types', () => {
    const hints = get(usePillSyntaxHints());
    expect(hints.keywords?.date).toBeDefined();
    expect(hints.keywords?.range).toBeDefined();
  });

  it('should cover both bounds and the span for an amount', () => {
    expect(get(usePillSyntaxHints()).examples?.range).toStrictEqual(['>100', '<10', '10 - 50']);
  });

  it('should cover both bounds and the span for a date', () => {
    set(dateInputFormat, DateFormat.DateMonthYearHourMinuteSecond);
    expect(dates()).toStrictEqual(['after 15/01/2024', 'before 15/01/2024', '15/01/2024 - 20/01/2024']);
  });
});
