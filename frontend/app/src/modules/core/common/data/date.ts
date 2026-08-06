import dayjs, { type Dayjs } from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';
import isToday from 'dayjs/plugin/isToday';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import relativeTime from 'dayjs/plugin/relativeTime';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import weekday from 'dayjs/plugin/weekday';
import weekOfYear from 'dayjs/plugin/weekOfYear';
import { markRaw, type Ref } from 'vue';
import { DateFormat } from '@/modules/core/common/date-format';

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

/**
 * The time part of the format, carrying only the precision the timestamp actually has: nothing for a
 * date on midnight, minutes once there is a time of day, and seconds or milliseconds below that.
 */
function timeFormatSuffix(time: Dayjs, enableMillisecond: boolean): string {
  const milliseconds = time.millisecond();
  const hasSubMinute = time.second() > 0 || milliseconds > 0;

  if (!hasSubMinute) {
    return time.hour() > 0 || time.minute() > 0 ? ' HH:mm' : '';
  }

  return enableMillisecond && milliseconds > 0 ? ' HH:mm:ss.SSS' : ' HH:mm:ss';
}

export function convertFromTimestamp(
  timestamp: number,
  dateFormat: DateFormat = DateFormat.DateMonthYearHourMinuteSecond,
  enableMillisecond: boolean = false,
): string {
  const time = dayjs(enableMillisecond ? timestamp : timestamp * 1000);

  return time.format(getDateInputISOFormat(dateFormat) + timeFormatSuffix(time, enableMillisecond));
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
  markRaw(dayjs.prototype);
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

function dateValidator(dateInputFormat: Ref<DateFormat>): (value: string) => boolean {
  return (value: string) => value.length > 0 && !isNaN(convertToTimestamp(value, get(dateInputFormat)));
}

/**
 * Validates a date string and ensures it respects a date range boundary.
 * For start dates, pass the end timestamp and `'start'` to ensure start <= end.
 * For end dates, pass the start timestamp and `'end'` to ensure end >= start.
 * Also rejects dates in the future.
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

    const timestamp = convertToTimestamp(value, get(dateInputFormat));

    const now = dayjs().unix();
    if (timestamp > now)
      return false;

    const otherBound = getOtherBound();
    if (!otherBound)
      return true;

    return type === 'start' ? timestamp <= Number(otherBound) : timestamp >= Number(otherBound);
  };
}

export function dateSerializer(dateInputFormat: Ref<DateFormat>): (date: string) => string {
  return (date: string) => convertToTimestamp(date, get(dateInputFormat)).toString();
}

/**
 * A written date read into the unix-second string a filter bound stores, or `undefined` when the
 * text is not a date. `dateSerializer` cannot say no: dayjs parses leniently and yields NaN for
 * nonsense, which would otherwise reach a filter as the literal string `NaN`.
 *
 * A date in the future is refused for the same reason `dateRangeValidator` refuses one: nothing has
 * happened yet after it, and the backend rejects a `from_timestamp` past its default `to_timestamp`
 * of now with a 400. The bar offers no filter for such a date rather than one that cannot load.
 */
export function dateBoundParser(dateInputFormat: Ref<DateFormat>): (value: string) => string | undefined {
  return (value: string): string | undefined => {
    const timestamp = convertToTimestamp(value, get(dateInputFormat));
    if (!Number.isFinite(timestamp) || timestamp <= 0 || timestamp > dayjs().unix())
      return undefined;
    return timestamp.toString();
  };
}

export function dateDeserializer(dateInputFormat: Ref<DateFormat>): (timestamp: string) => string {
  return (timestamp: string) => convertFromTimestamp(parseInt(timestamp), get(dateInputFormat));
}
