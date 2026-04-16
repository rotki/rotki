import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { DateFormatter } from '@/modules/core/common/date-formatter';

describe('date-formatter', () => {
  const converter = new DateFormatter();
  let date: Date;
  let originalOffset: () => number;

  function overrideTimezoneOffset(offset: number): void {
    // eslint-disable-next-line no-extend-native
    Date.prototype.getTimezoneOffset = (): number => offset;
  }

  beforeEach((): void => {
    // eslint-disable-next-line @typescript-eslint/unbound-method
    originalOffset = Date.prototype.getTimezoneOffset;
    overrideTimezoneOffset(0);
    date = new Date(Date.parse('03 Feb 2019 13:09:09 UTC'));
  });

  afterEach((): void => {
    // eslint-disable-next-line no-extend-native
    Date.prototype.getTimezoneOffset = originalOffset;
  });

  it('should return the day in short form if the pattern is %a', () => {
    expect(converter.format(date, '%a')).toBe('Sun');
  });

  it('should return the day in long form if the pattern is %A', () => {
    expect(converter.format(date, '%A')).toBe('Sunday');
  });

  it('should return the day in numeric if the pattern is %w', () => {
    expect(converter.format(date, '%w')).toBe('0');
  });

  it('should return the year in 2-digit format if the pattern is %y', () => {
    expect(converter.format(date, '%y')).toBe('19');
  });

  it('should return the year in full format if the pattern is %Y', () => {
    expect(converter.format(date, '%Y')).toBe('2019');
  });

  it('should return the month in short format if the pattern is %b', () => {
    expect(converter.format(date, '%b')).toBe('Feb');
  });

  it('should return the month in full format if the pattern is %B', () => {
    expect(converter.format(date, '%B')).toBe('February');
  });

  it('should return the month in 2-digit format if the pattern is %m', () => {
    expect(converter.format(date, '%m')).toBe('02');
  });

  it('should return the month in numeric format if the pattern is %-m', () => {
    expect(converter.format(date, '%-m')).toBe('2');
  });

  it('should return the day in 2-digit format if the pattern is %d', () => {
    expect(converter.format(date, '%d')).toBe('03');
  });

  it('should return the day in numeric format if the pattern is %-d', () => {
    expect(converter.format(date, '%-d')).toBe('3');
  });

  it('should return the hour in 2-digit format if the pattern is %H', () => {
    date.setHours(8);
    expect(converter.format(date, '%H')).toBe('08');
  });

  it('should return the hour in numeric format if the pattern is %-H', () => {
    date.setHours(8);
    expect(converter.format(date, '%-H')).toBe('8');
  });

  it('should return the hours in 12-hour 2-digit format if the pattern is %I', () => {
    expect(converter.format(date, '%I')).toBe('01');
  });

  it('should return the hours in 12-hour numeric format if the pattern is %-I', () => {
    expect(converter.format(date, '%-I')).toBe('1');
  });

  it('should return the minutes in 2-digit format if the pattern is %M', () => {
    expect(converter.format(date, '%M')).toBe('09');
  });

  it('should return the minutes in numeric format if the pattern is %-M', () => {
    expect(converter.format(date, '%-M')).toBe('9');
  });

  it('should return the seconds in 2-digit format if the pattern is %S', () => {
    expect(converter.format(date, '%S')).toBe('09');
  });

  it('should return the seconds in numeric format if the pattern is %-S', () => {
    expect(converter.format(date, '%-S')).toBe('9');
  });

  it('should return the am/pm if the pattern is %p', () => {
    expect(converter.format(date, '%p')).toBe('PM');
    date.setTime(8);
    expect(converter.format(date, '%p')).toBe('AM');
  });

  it('should return the timezone if the pattern is %z', () => {
    expect(converter.format(date, '%z')).toBe('+0000');
    overrideTimezoneOffset(+120);
    expect(converter.format(new Date('2019-02-03T13:09:09-02:00'), '%z')).toBe('-0200');
  });

  it('should return the timezone if the pattern is %Z', () => {
    expect(converter.format(date, '%Z')).toMatch(/^UTC|GMT$/);
  });

  it('should return the day of the year padded if the pattern is %j', () => {
    expect(converter.format(date, '%j')).toBe('034');
  });

  it('should return the day of the year if the pattern is %-j', () => {
    expect(converter.format(date, '%-j')).toBe('34');
  });

  it('should return the locale’s appropriate date and time representation if the pattern is %c', () => {
    expect(converter.format(date, '%c')).toBe('2/3/2019, 1:09:09 PM');
  });

  it('should return the locale’s appropriate date representation if the pattern is %x', () => {
    expect(converter.format(date, '%x')).toBe('2/3/2019');
  });

  it('should return the locale’s appropriate time representation if the pattern is %X', () => {
    expect(converter.format(date, '%X')).toBe('1:09:09 PM');
  });
});
