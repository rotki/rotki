import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';

export function convertToTimestamp(date: string): number {
  let format: string = 'DD/MM/YYYY';
  if (date.indexOf(' ') > -1) {
    format += ' HH:mm';
    if (date.charAt(date.length - 6) === ':') {
      format += ':ss';
    }
  }

  return dayjs(date, format).unix();
}

export function convertFromTimestamp(
  timestamp: number,
  seconds: boolean = false
): string {
  let format = 'DD/MM/YYYY HH:mm';
  if (seconds) {
    format += ':ss';
  }

  return dayjs(timestamp * 1000).format(format);
}

export function setupDayjs() {
  dayjs.extend(customParseFormat);
  dayjs.extend(utc);
  dayjs.extend(timezone);
  dayjs.extend(localizedFormat);
  dayjs.tz.guess();
}
