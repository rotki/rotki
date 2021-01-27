import moment from 'moment';

export function convertToTimestamp(date: string): number {
  let format: string = 'DD/MM/YYYY';
  if (date.indexOf(' ') > -1) {
    format += ' HH:mm';
    if (date.charAt(date.length - 6) === ':') {
      format += ':ss';
    }
  }

  return moment(date, format).unix();
}

export function convertFromTimestamp(
  timestamp: number,
  seconds: boolean = false
): string {
  let format = 'DD/MM/YYYY HH:mm';
  if (seconds) {
    format += ':ss';
  }

  return moment(timestamp * 1000).format(format);
}
