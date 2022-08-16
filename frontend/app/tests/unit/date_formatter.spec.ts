import { DateFormatter } from '@/data/date_formatter';

describe('DateFormatter', function () {
  const converter = new DateFormatter();
  let date: Date;
  let originalOffset: () => number;

  function overrideTimezoneOffset(offset: number) {
    Date.prototype.getTimezoneOffset = () => offset;
  }

  beforeEach(() => {
    originalOffset = Date.prototype.getTimezoneOffset;
    overrideTimezoneOffset(0);
    date = new Date(Date.parse('03 Feb 2019 13:09:09 UTC'));
  });

  afterEach(function () {
    Date.prototype.getTimezoneOffset = originalOffset;
  });

  test('should return the day in short form if the pattern is %a', function () {
    expect(converter.format(date, '%a')).toEqual('Sun');
  });

  test('should return the day in long form if the pattern is %A', function () {
    expect(converter.format(date, '%A')).toEqual('Sunday');
  });

  test('should return the day in numeric if the pattern is %w', function () {
    expect(converter.format(date, '%w')).toEqual('0');
  });

  test('should return the year in 2-digit format if the pattern is %y', function () {
    expect(converter.format(date, '%y')).toEqual('19');
  });

  test('should return the year in full format if the pattern is %Y', function () {
    expect(converter.format(date, '%Y')).toEqual('2019');
  });

  test('should return the month in short format if the pattern is %b', function () {
    expect(converter.format(date, '%b')).toEqual('Feb');
  });

  test('should return the month in full format if the pattern is %B', function () {
    expect(converter.format(date, '%B')).toEqual('February');
  });

  test('should return the month in 2-digit format if the pattern is %m', function () {
    expect(converter.format(date, '%m')).toEqual('02');
  });

  test('should return the month in numeric format if the pattern is %-m', function () {
    expect(converter.format(date, '%-m')).toEqual('2');
  });

  test('should return the day in 2-digit format if the pattern is %d', function () {
    expect(converter.format(date, '%d')).toEqual('03');
  });

  test('should return the day in numeric format if the pattern is %-d', function () {
    expect(converter.format(date, '%-d')).toEqual('3');
  });

  test('should return the hour in 2-digit format if the pattern is %H', function () {
    date.setHours(8);
    expect(converter.format(date, '%H')).toEqual('08');
  });

  test('should return the hour in numeric format if the pattern is %-H', function () {
    date.setHours(8);
    expect(converter.format(date, '%-H')).toEqual('8');
  });

  test('should return the hours in 12-hour 2-digit format if the pattern is %I', function () {
    expect(converter.format(date, '%I')).toEqual('01');
  });

  test('should return the hours in 12-hour numeric format if the pattern is %-I', function () {
    expect(converter.format(date, '%-I')).toEqual('1');
  });

  test('should return the minutes in 2-digit format if the pattern is %M', function () {
    expect(converter.format(date, '%M')).toEqual('09');
  });

  test('should return the minutes in numeric format if the pattern is %-M', function () {
    expect(converter.format(date, '%-M')).toEqual('9');
  });

  test('should return the seconds in 2-digit format if the pattern is %S', function () {
    expect(converter.format(date, '%S')).toEqual('09');
  });

  test('should return the seconds in numeric format if the pattern is %-S', function () {
    expect(converter.format(date, '%-S')).toEqual('9');
  });

  test('should return the am/pm if the pattern is %p', function () {
    expect(converter.format(date, '%p')).toEqual('PM');
    date.setTime(8);
    expect(converter.format(date, '%p')).toEqual('AM');
  });

  test('should return the timezone if the pattern is %z', function () {
    expect(converter.format(date, '%z')).toEqual('+0000');
    overrideTimezoneOffset(+120);
    expect(
      converter.format(new Date('2019-02-03T13:09:09-02:00'), '%z')
    ).toEqual('-0200');
  });

  test('should return the timezone if the pattern is %Z', function () {
    expect(converter.format(date, '%Z')).toMatch(/^UTC|GMT$/);
  });

  test('should return the day of the year padded if the pattern is %j', function () {
    expect(converter.format(date, '%j')).toEqual('034');
  });

  test('should return the day of the year if the pattern is %-j', function () {
    expect(converter.format(date, '%-j')).toEqual('34');
  });

  test('should return the locale’s appropriate date and time representation if the pattern is %c', function () {
    expect(converter.format(date, '%c')).toEqual('2/3/2019, 1:09:09 PM');
  });

  test('should return the locale’s appropriate date representation if the pattern is %x', function () {
    expect(converter.format(date, '%x')).toEqual('2/3/2019');
  });

  test('should return the locale’s appropriate time representation if the pattern is %X', function () {
    expect(converter.format(date, '%X')).toEqual('1:09:09 PM');
  });
});
