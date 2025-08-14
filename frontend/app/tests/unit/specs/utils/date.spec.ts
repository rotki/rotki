import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import { DateFormat } from '@/types/date-format';
import {
  convertFromTimestamp,
  convertToTimestamp,
  getDayNames,
  setupDayjs,
} from '@/utils/date';

describe('utils/date', () => {
  setupDayjs();

  describe('convertToTimestamp', () => {
    // Basic functionality: Correct conversion to timestamp
    it('converts a date to a timestamp correctly', () => {
      const date = '02/01/2023 12:34:56';
      const expectedTimestamp = dayjs('2023-01-02T12:34:56').unix();
      expect(convertToTimestamp(date, DateFormat.DateMonthYearHourMinuteSecond)).toBe(expectedTimestamp);
    });

    // Handling milliseconds
    it('handles milliseconds correctly when enabled', () => {
      const dateWithMilliseconds = '01/02/2023 12:34:56.789';
      const expectedTimestamp = dayjs('2023-02-01T12:34:56.789').valueOf();
      expect(convertToTimestamp(dateWithMilliseconds, DateFormat.DateMonthYearHourMinuteSecond, true)).toBe(
        expectedTimestamp,
      );
    });

    // Edge case: Leap second
    it('handles leap second', () => {
      const leapSecondDate = '30/06/2015 23:59:60'; // Leap second on 30 June 2015
      const timestamp = convertToTimestamp(leapSecondDate, DateFormat.DateMonthYearHourMinuteSecond);
      expect(timestamp).toBeGreaterThan(0); // Simple check to ensure conversion happened
    });

    // Invalid input: Incorrect format
    it('returns NaN for dates with incorrect format', () => {
      const incorrectFormatDate = '2023-02-01';
      expect(convertToTimestamp(incorrectFormatDate, DateFormat.DateMonthYearHourMinuteSecond)).toBeNaN();
    });

    // Handling empty date input
    it('returns NaN for null or empty date input', () => {
      expect(convertToTimestamp('', DateFormat.DateMonthYearHourMinuteSecond)).toBeNaN();
    });
  });

  describe('convertFromTimestamp', () => {
    // Basic functionality: Correct conversion from UNIX timestamp
    it('converts a UNIX timestamp to a date string correctly', () => {
      const timestamp = dayjs('2023-04-15T12:34:56').unix();
      const expectedDate = '15/04/2023 12:34:56';
      expect(convertFromTimestamp(timestamp, DateFormat.DateMonthYearHourMinuteSecond)).toBe(expectedDate);
    });

    // Handling milliseconds
    it('converts a timestamp with milliseconds to a date string correctly', () => {
      const timestampWithMilliseconds = dayjs('2023-04-15T12:34:56.789').valueOf();
      const expectedDateWithMilliseconds = '15/04/2023 12:34:56.789';
      expect(convertFromTimestamp(timestampWithMilliseconds, DateFormat.DateMonthYearHourMinuteSecond, true)).toBe(
        expectedDateWithMilliseconds,
      );
    });

    // Edge case: Start of UNIX epoch
    it('handles the start of UNIX epoch correctly', () => {
      const startOfUnixEpoch = 0;
      const expectedDate = '01/01/1970'; // UTC time
      expect(convertFromTimestamp(startOfUnixEpoch, DateFormat.DateMonthYearHourMinuteSecond)).toBe(expectedDate);
    });

    // Edge case: Turn of the millennium
    it('handles the turn of the millennium correctly', () => {
      const turnOfMillennium = dayjs('2000-01-01T00:00:00').unix();
      const expectedDate = '01/01/2000';
      expect(convertFromTimestamp(turnOfMillennium, DateFormat.DateMonthYearHourMinuteSecond)).toBe(expectedDate);
    });

    // Invalid input: Negative timestamp (before UNIX epoch)
    it('handles negative timestamps correctly', () => {
      const negativeTimestamp = dayjs('1969-12-31T23:59:59').unix();
      const expectedDate = '31/12/1969 23:59:59';
      expect(convertFromTimestamp(negativeTimestamp, DateFormat.DateMonthYearHourMinuteSecond)).toBe(expectedDate);
    });

    // Extreme case: Far future timestamp
    it('handles far future timestamps correctly', () => {
      const farFutureTimestamp = dayjs('9999-12-31T23:59:59').unix();
      const expectedDate = '31/12/9999 23:59:59';
      expect(convertFromTimestamp(farFutureTimestamp, DateFormat.DateMonthYearHourMinuteSecond)).toBe(expectedDate);
    });

    // Edge case: Very end of the day (one second before midnight)
    it('handles times just before midnight correctly', () => {
      const timestampJustBeforeMidnight = dayjs('2023-04-15T23:59:59').unix();
      const expectedDate = '15/04/2023 23:59:59';
      expect(convertFromTimestamp(timestampJustBeforeMidnight, DateFormat.DateMonthYearHourMinuteSecond)).toBe(
        expectedDate,
      );
    });
  });

  describe('getDayNames', () => {
    const result = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    it('works in current timezone', () => {
      expect(getDayNames('en')).toStrictEqual(result);
    });

    it('works in New York timezone', () => {
      // eslint-disable-next-line no-extend-native
      Date.prototype.getTimezoneOffset = function () {
        return -240;
      };

      expect(getDayNames('en')).toStrictEqual(result);

      // eslint-disable-next-line no-extend-native
      Date.prototype.getTimezoneOffset = function () {
        return 0;
      };
    });
  });
});
