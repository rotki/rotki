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
  toFormat: DateFormat
): string {
  if (!date) {
    return '';
  }

  const timestamp = convertToTimestamp(date, fromFormat);

  return convertFromTimestamp(timestamp, toFormat);
}

export function convertToTimestamp(
  date: string,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond
): number {
  let format: string = getDateInputISOFormat(dateFormat);
  const firstSplit = date.split(' ');
  if (firstSplit.length === 2) {
    format += ' HH:mm';

    const secondSplit = firstSplit[1].split(':');
    if (secondSplit.length === 3) {
      format += ':ss';

      const thirdSplit = secondSplit[2].split('.');
      if (thirdSplit.length === 2) {
        format += '.SSS';
      }
    }
  }

  return dayjs(date, format).valueOf() / 1000;
}

export function convertFromTimestamp(
  timestamp: number,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond
): string {
  const time = dayjs(timestamp * 1000);
  let format: string = getDateInputISOFormat(dateFormat);
  format += ' HH:mm:ss';

  if (time.millisecond() > 0) {
    format += '.SSS';
  }

  return time.format(format);
}

export function convertDateByTimezone(
  date: string,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  fromTimezone: string,
  toTimezone: string
): string {
  if (!date) {
    return date;
  }

  fromTimezone = fromTimezone || dayjs.tz.guess();
  toTimezone = toTimezone || dayjs.tz.guess();

  let format: string = getDateInputISOFormat(dateFormat);
  const firstSplit = date.split(' ');
  if (firstSplit.length === 2) {
    format += ' HH:mm';

    const secondSplit = firstSplit[1].split(':');
    if (secondSplit.length === 3) {
      format += ':ss';

      const thirdSplit = secondSplit[2].split('.');
      if (thirdSplit.length === 2) {
        format += '.SSS';
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
