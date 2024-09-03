import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import weekday from 'dayjs/plugin/weekday';
import weekOfYear from 'dayjs/plugin/weekOfYear';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isToday from 'dayjs/plugin/isToday';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import relativeTime from 'dayjs/plugin/relativeTime';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import { DateFormat } from '@/types/date-format';
import { timezones } from '@/data/timezones';

export function guessTimezone(): string {
  const guessedTimezone = dayjs.tz.guess();
  const offset = dayjs().utcOffset();
  const timezone = timezones.find(tz => tz === guessedTimezone);

  const hour = Math.round(offset / 60);
  const isNegative = hour < 0;
  return timezone ?? `ETC/GMT${isNegative ? '' : '+'}${hour}`;
}

export function getDateInputISOFormat(format: DateFormat): string {
  return {
    [DateFormat.DateMonthYearHourMinuteSecondTimezone]: 'DD/MM/YYYY',
    [DateFormat.DateMonthYearHourMinuteSecond]: 'DD/MM/YYYY',
    [DateFormat.MonthDateYearHourMinuteSecond]: 'MM/DD/YYYY',
    [DateFormat.YearMonthDateHourMinuteSecond]: 'YYYY/MM/DD',
  }[format];
}

export function changeDateFormat(
  date: string,
  fromFormat: DateFormat,
  toFormat: DateFormat,
  milliseconds: boolean = false,
): string {
  if (!date)
    return '';

  if (fromFormat === toFormat)
    return date;

  const timestamp = convertToTimestamp(date, fromFormat, milliseconds);

  return convertFromTimestamp(timestamp, toFormat, milliseconds);
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

export function convertDateByTimezone(
  date: string,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  fromTimezone: string,
  toTimezone: string,
  milliseconds: boolean = false,
): string {
  if (!date)
    return date;

  fromTimezone = fromTimezone || guessTimezone();
  toTimezone = toTimezone || guessTimezone();

  if (fromTimezone === toTimezone)
    return date;

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

  return dayjs.tz(date, format, fromTimezone).tz(toTimezone).format(format);
}

export function isValidDate(date: string, dateFormat: string): boolean {
  if (!date)
    return false;

  return dayjs(date, dateFormat, true).isValid();
}

export function getDayNames(locale = 'en'): string[] {
  const format = new Intl.DateTimeFormat(locale, { weekday: 'short', timeZone: 'UTC' });
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
