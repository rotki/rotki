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

export function convertFromTimestamp(timestamp: number): string {
  return moment(timestamp * 1000).format('DD/MM/YYYY HH:mm');
}
