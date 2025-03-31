import { DateFormat } from '@/types/date-format';
import {
  convertFromTimestamp,
  convertTimestampByTimezone,
  convertToTimestamp,
  getDayNames,
  guessTimezone,
  isValidDate,
  setupDayjs,
} from '@/utils/date';
import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';

describe('utils/date', () => {
  setupDayjs();
  describe('guessTimezone', () => {
    it('check return value of guessTimezone function', () => {
      expect(guessTimezone()).toBeTruthy();
      expect(guessTimezone()).toBeTypeOf('string');
    });

    it('check converted date matches with timezone applied', () => {
      const utcDate = dayjs.utc('2013-11-18 11:55:20').tz(guessTimezone()).toString();
      const utcTzDate = dayjs.utc('2013-11-18 11:55:20').toString();
      expect(utcDate).toEqual(utcTzDate);
    });
  });

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

  describe('convertTimestampByTimezone', () => {
    // Basic functionality: Time zone conversion
    it('converts timestamps between time zones correctly', () => {
      const timestamp = 1672531200; // 01/01/2023 00:00:00 UTC
      const fromTimezone = 'UTC';
      const toTimezone = 'America/New_York'; // UTC-5 typically
      const convertedTimestamp = convertTimestampByTimezone(
        timestamp,
        fromTimezone,
        toTimezone,
      );
      // Expect the timestamp to be adjusted by 5 hours (18000 seconds)
      expect(convertedTimestamp).toBe(1672531200 - 18000);
    });

    // Handling Daylight Saving Time start (Spring forward)
    it('adjusts correctly for the start of Daylight Saving Time', () => {
      const timestamp = 1615698600; // 14/03/2021 02:30:00 UTC
      const fromTimezone = 'UTC';
      const toTimezone = 'America/New_York'; // UTC-4 during DST
      const convertedTimestamp = convertTimestampByTimezone(
        timestamp,
        fromTimezone,
        toTimezone,
      );
      // Adjusted by 4 hours (14400 seconds) due to DST
      expect(convertedTimestamp).toBe(1615698600 - 14400);
    });

    // Handling Daylight Saving Time end (Fall back)
    it('adjusts correctly for the end of Daylight Saving Time', () => {
      const timestamp = 1636247400; // 07/11/2021 01:30:00 UTC
      const fromTimezone = 'UTC';
      const toTimezone = 'America/New_York';
      const convertedTimestamp = convertTimestampByTimezone(
        timestamp,
        fromTimezone,
        toTimezone,
      );
      // Adjusted by 4 hours (14400 seconds) as still in DST
      expect(convertedTimestamp).toBe(1636247400 - 14400);
    });

    // Test with milliseconds parameter enabled
    it('handles timestamps with milliseconds correctly', () => {
      const timestampMs = 1672531200123; // Timestamp with milliseconds
      const fromTimezone = 'UTC';
      const toTimezone = 'America/New_York';
      const convertedTimestamp = convertTimestampByTimezone(
        timestampMs,
        fromTimezone,
        toTimezone,
        true,
      );
      // Adjusted by 5 hours (18000000 milliseconds)
      expect(convertedTimestamp).toBe(1672531200123 - 18000000);
    });

    // Test with same source and destination timezone
    it('returns the original timestamp when timezones are the same', () => {
      const timestamp = 1672531200;
      const timezone = 'UTC';
      const convertedTimestamp = convertTimestampByTimezone(
        timestamp,
        timezone,
        timezone,
      );
      expect(convertedTimestamp).toBe(timestamp);
    });

    // Invalid input: Unsupported or incorrect time zone identifiers
    it('throws an error for invalid timezone identifiers', () => {
      const timestamp = 1672531200;
      const fromTimezone = 'Invalid/Timezone';
      const toTimezone = 'Also/Invalid';
      expect(() =>
        convertTimestampByTimezone(timestamp, fromTimezone, toTimezone),
      ).toThrow();
    });
  });

  describe('isValidDate', () => {
    // Basic functionality: Valid dates in different formats
    it('validates correctly formatted dates', () => {
      expect(isValidDate('01/02/2023', 'DD/MM/YYYY')).toBeTruthy();
      expect(isValidDate('2023-02-01', 'YYYY-MM-DD')).toBeTruthy();
    });

    // Handling leap years
    it('correctly identifies leap year dates as valid', () => {
      expect(isValidDate('29/02/2020', 'DD/MM/YYYY')).toBeTruthy(); // 2020 is a leap year
      expect(isValidDate('29/02/2024', 'DD/MM/YYYY')).toBeTruthy(); // 2024 is also a leap year
    });

    // Non-leap years
    it('rejects February 29 on non-leap years', () => {
      expect(isValidDate('29/02/2023', 'DD/MM/YYYY')).toBeFalsy(); // 2023 is not a leap year
      expect(isValidDate('29/02/2021', 'DD/MM/YYYY')).toBeFalsy(); // 2021 is not a leap year
    });

    // Boundary conditions: Start and end of a month
    it('validates dates at the start and end of months correctly', () => {
      expect(isValidDate('01/01/2023', 'DD/MM/YYYY')).toBeTruthy(); // Start of January
      expect(isValidDate('31/01/2023', 'DD/MM/YYYY')).toBeTruthy(); // End of January
      expect(isValidDate('30/04/2023', 'DD/MM/YYYY')).toBeTruthy(); // End of April
      expect(isValidDate('31/04/2023', 'DD/MM/YYYY')).toBeFalsy(); // April has 30 days
    });

    // Boundary conditions: Start and end of a year
    it('validates dates at the start and end of years correctly', () => {
      expect(isValidDate('01/01/2023', 'DD/MM/YYYY')).toBeTruthy(); // Start of the year
      expect(isValidDate('31/12/2023', 'DD/MM/YYYY')).toBeTruthy(); // End of the year
    });

    // Invalid input: Garbled or nonsensical strings
    it('returns false for garbled date strings', () => {
      expect(isValidDate('not-a-date', 'DD/MM/YYYY')).toBeFalsy();
    });

    // Invalid input: Incorrectly formatted dates
    it('returns false for dates not matching the format', () => {
      expect(isValidDate('2023/01/02', 'DD/MM/YYYY')).toBeFalsy(); // Incorrect separator and format order
      expect(isValidDate('02-01-2023', 'DD/MM/YYYY')).toBeFalsy(); // Incorrect separator
    });

    // Handling null or empty date input
    it('returns false for null or empty date input', () => {
      expect(isValidDate('', 'DD/MM/YYYY')).toBeFalsy();
    });

    // Specific format: Testing different separators
    it('validates dates with specific separators correctly', () => {
      expect(isValidDate('01-02-2023', 'DD-MM-YYYY')).toBeTruthy(); // Dash separator
      expect(isValidDate('01/02/2023', 'DD-MM-YYYY')).toBeFalsy(); // Incorrect separator for the given format
    });

    // Edge case: Date and month transposition
    it('detects invalid dates due to day-month transposition', () => {
      expect(isValidDate('13/13/2023', 'DD/MM/YYYY')).toBeFalsy(); // Both values are out of valid ranges for day and month
    });

    // Extreme dates: Historical and far future dates
    it('handles historical and far future dates', () => {
      expect(isValidDate('01/01/1000', 'DD/MM/YYYY')).toBeTruthy(); // Historical date
      expect(isValidDate('01/01/3000', 'DD/MM/YYYY')).toBeTruthy(); // Far future date
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
