import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import isToday from 'dayjs/plugin/isToday';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import { DateFormat } from '@/types/date-format';

export function getDateInputISOFormat(format: DateFormat): string {
  return {
    [DateFormat.DateMonthYearHourMinuteSecondTimezone]: 'DD/MM/YYYY',
    [DateFormat.DateMonthYearHourMinuteSecond]: 'DD/MM/YYYY',
    [DateFormat.MonthDateYearHourMinuteSecond]: 'MM/DD/YYYY',
    [DateFormat.YearMonthDateHourMinuteSecond]: 'YYYY/MM/DD'
  }[format];
}

export function changeDateFormat(
  date: string,
  fromFormat: DateFormat,
  toFormat: DateFormat,
  milliseconds: boolean = false
): string {
  if (!date) {
    return '';
  }

  const timestamp = convertToTimestamp(date, fromFormat, milliseconds);

  return convertFromTimestamp(timestamp, toFormat, milliseconds);
}

export function convertToTimestamp(
  date: string,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  milliseconds: boolean = false
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
        if (thirdSplit.length === 2) {
          format += '.SSS';
        }
      }
    }
  }

  if (milliseconds) {
    return dayjs(date, format).valueOf();
  }

  return dayjs(date, format).unix();
}

export function convertFromTimestamp(
  timestamp: number,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  milliseconds: boolean = false
): string {
  const time = dayjs(milliseconds ? timestamp : timestamp * 1000);
  let format: string = getDateInputISOFormat(dateFormat);
  format += ' HH:mm:ss';

  if (milliseconds && time.millisecond() > 0) {
    format += '.SSS';
  }

  return time.format(format);
}

export function convertDateByTimezone(
  date: string,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  fromTimezone: string,
  toTimezone: string,
  milliseconds: boolean = false
): string {
  if (!date) {
    return date;
  }

  fromTimezone = fromTimezone || dayjs.tz.guess();
  toTimezone = toTimezone || dayjs.tz.guess();

  if (fromTimezone === toTimezone) {
    return date;
  }

  let format: string = getDateInputISOFormat(dateFormat);
  const firstSplit = date.split(' ');
  if (firstSplit.length === 2) {
    format += ' HH:mm';

    const secondSplit = firstSplit[1].split(':');
    if (secondSplit.length === 3) {
      format += ':ss';

      if (milliseconds) {
        const thirdSplit = secondSplit[2].split('.');
        if (thirdSplit.length === 2) {
          format += '.SSS';
        }
      }
    }
  }

  return dayjs.tz(date, format, fromTimezone).tz(toTimezone).format(format);
}

export function isValidDate(date: string, dateFormat: string): boolean {
  if (!date) {
    return false;
  }
  return dayjs(date, dateFormat, true).isValid();
}

export function setupDayjs(): void {
  dayjs.extend(customParseFormat);
  dayjs.extend(utc);
  dayjs.extend(timezone);
  dayjs.extend(localizedFormat);
  dayjs.extend(isToday);
  dayjs.tz.guess();
}
