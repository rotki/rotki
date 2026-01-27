import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isToday from 'dayjs/plugin/isToday';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import relativeTime from 'dayjs/plugin/relativeTime';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import weekday from 'dayjs/plugin/weekday';
import weekOfYear from 'dayjs/plugin/weekOfYear';
import type { Ref } from 'vue';
import { DateFormat } from '@/types/date-format';

export function getDateInputISOFormat(format: DateFormat): string {
  return {
    [DateFormat.DateMonthYearHourMinuteSecond]: 'DD/MM/YYYY',
    [DateFormat.DateMonthYearHourMinuteSecondTimezone]: 'DD/MM/YYYY',
    [DateFormat.MonthDateYearHourMinuteSecond]: 'MM/DD/YYYY',
    [DateFormat.YearMonthDateHourMinuteSecond]: 'YYYY/MM/DD',
  }[format];
}

export function convertToTimestamp(
  date: string,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  milliseconds: boolean = false,
): number {
  let format: string = getDateInputISOFormat(dateFormat);
  const firstSplit = date.split(' ');
  if (firstSplit.length === 2) {
    format += ' HH:mm';

    const secondSplit = firstSplit[1].split(':');
    if (secondSplit.length === 3) {
      format += ':ss';

      if (milliseconds) {
        const thirdSplit = secondSplit[2].split('.');
        if (thirdSplit.length === 2)
          format += '.SSS';
      }
    }
  }

  if (milliseconds)
    return dayjs(date, format).valueOf();

  return dayjs(date, format).unix();
}

export function convertFromTimestamp(
  timestamp: number,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  enableMillisecond: boolean = false,
): string {
  const time = dayjs(enableMillisecond ? timestamp : timestamp * 1000);
  let format: string = getDateInputISOFormat(dateFormat);
  const seconds = time.second();
  const hours = time.hour();
  const minutes = time.minute();
  const milliseconds = time.millisecond();

  if (hours > 0 || minutes > 0 || seconds > 0 || milliseconds > 0) {
    format += ' HH:mm';

    if (seconds > 0 || milliseconds > 0) {
      format += ':ss';

      if (enableMillisecond && milliseconds > 0)
        format += '.SSS';
    }
  }

  return time.format(format);
}

export function getDayNames(locale = 'en'): string[] {
  const format = new Intl.DateTimeFormat(locale, { timeZone: 'UTC', weekday: 'short' });
  const days = [];
  for (let day = 1; day <= 7; day++) {
    const date = new Date(Date.UTC(2022, 0, day + 2)); // +2 because 2022-01-02 is a Sunday
    days.push(format.format(date));
  }
  return days;
}

export function setupDayjs(): void {
  dayjs.extend(customParseFormat);
  dayjs.extend(utc);
  dayjs.extend(timezone);
  dayjs.extend(localizedFormat);
  dayjs.extend(isToday);
  dayjs.extend(weekday);
  dayjs.extend(weekOfYear);
  dayjs.extend(isSameOrAfter);
  dayjs.extend(relativeTime);
}

export function millisecondsToSeconds(milliseconds: number): number {
  return Math.floor(milliseconds / 1000);
}

export function dateValidator(dateInputFormat: Ref<DateFormat>): (value: string) => boolean {
  return (value: string) => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat)));
}

/**
 * Validates a date string and ensures it respects a date range boundary.
 * For start dates, pass the end timestamp and `'start'` to ensure start <= end.
 * For end dates, pass the start timestamp and `'end'` to ensure end >= start.
 */
export function dateRangeValidator(
  dateInputFormat: Ref<DateFormat>,
  getOtherBound: () => string | undefined,
  type: 'start' | 'end',
): (value: string) => boolean {
  const baseValidator = dateValidator(dateInputFormat);
  return (value: string): boolean => {
    if (!baseValidator(value))
      return false;

    const otherBound = getOtherBound();
    if (!otherBound)
      return true;

    const timestamp = convertToTimestamp(value, get(dateInputFormat));
    return type === 'start' ? timestamp <= Number(otherBound) : timestamp >= Number(otherBound);
  };
}

export function dateSerializer(dateInputFormat: Ref<DateFormat>): (date: string) => string {
  return (date: string) => convertToTimestamp(date, get(dateInputFormat)).toString();
}

export function dateDeserializer(dateInputFormat: Ref<DateFormat>): (timestamp: string) => string {
  return (timestamp: string) => convertFromTimestamp(parseInt(timestamp), get(dateInputFormat));
}
