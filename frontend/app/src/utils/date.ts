import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import isToday from 'dayjs/plugin/isToday';
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
  const time = dayjs(timestamp * 1000);
  let format = 'DD/MM/YYYY';
  if (time.hour() !== 0 || time.minute() !== 0) {
    format += ' HH:mm';
    if (seconds && time.second() !== 0) {
      format += ':ss';
    }
  }

  return time.format(format);
}

export function setupDayjs() {
  dayjs.extend(customParseFormat);
  dayjs.extend(utc);
  dayjs.extend(timezone);
  dayjs.extend(localizedFormat);
  dayjs.extend(isToday);
  dayjs.tz.guess();
}
