export class DateFormatter {
  private regex = /%-?[A-Za-z]/gm;
  private translations: Record<
    string,
    (date: Date, locale?: string) => string
  > = {
    a: (date, locale) => date.toLocaleDateString(locale, { weekday: 'short' }),
    A: (date, locale) => date.toLocaleDateString(locale, { weekday: 'long' }),
    w: date => date.getDay().toString(),
    y: (date, locale) => date.toLocaleDateString(locale, { year: '2-digit' }),
    Y: (date, locale) => date.toLocaleDateString(locale, { year: 'numeric' }),
    b: (date, locale) => date.toLocaleDateString(locale, { month: 'short' }),
    B: (date, locale) => date.toLocaleDateString(locale, { month: 'long' }),
    m: (date, locale) => date.toLocaleDateString(locale, { month: '2-digit' }),
    '-m': (date, locale) =>
      date.toLocaleDateString(locale, { month: 'numeric' }),
    d: (date, locale) => date.toLocaleDateString(locale, { day: '2-digit' }),
    '-d': (date, locale) => date.toLocaleDateString(locale, { day: 'numeric' }),
    H: date => DateFormatter.leftPad(date.getHours().toString()),
    '-H': date => date.getHours().toString(),
    I: date => DateFormatter.leftPad(DateFormatter.twelveHours(date)),
    '-I': date => DateFormatter.twelveHours(date),
    M: date => DateFormatter.leftPad(date.getMinutes().toString()),
    '-M': date => date.getMinutes().toString(),
    S: date => DateFormatter.leftPad(date.getSeconds().toString()),
    '-S': date => date.getSeconds().toString(),
    s: date => DateFormatter.leftPad(date.getMilliseconds().toString(), 3),
    p: (date, locale) => DateFormatter.amPm(date, locale),
    z: date => DateFormatter.timezoneOffset(date),
    Z: (date, locale) => DateFormatter.timezone(date, locale),
    j: date =>
      DateFormatter.leftPad(DateFormatter.dayOfTheYear(date).toString(), 3),
    '-j': date => DateFormatter.dayOfTheYear(date).toString(),
    c: (date, locale) => date.toLocaleString(locale),
    x: (date, locale) => date.toLocaleDateString(locale),
    X: (date, locale) => date.toLocaleTimeString(locale),
    '%': () => '%'
  };

  private static leftPad(text: string, length = 2, padString = '0'): string {
    let paddedText = text;
    while (paddedText.length < length) {
      paddedText = padString + paddedText;
    }
    return paddedText;
  }

  private static twelveHours(date: Date): string {
    let hours: number = date.getHours();
    if (hours > 12) {
      hours = date.getHours() - 12;
    }
    return hours.toString();
  }

  private static dayOfTheYear(date: Date): number {
    const start = new Date(date.getFullYear(), 0, 0);
    const diff =
      date.getTime() -
      start.getTime() +
      (start.getTimezoneOffset() - date.getTimezoneOffset()) * 60 * 1000;
    const oneDay = 1000 * 60 * 60 * 24;
    return Math.floor(diff / oneDay);
  }

  private static amPm(date: Date, locale?: string): string {
    const timeString = date.toLocaleTimeString(locale, { hour12: true });
    return timeString.slice(-2);
  }

  private static timezone(date: Date, locale?: string): string {
    const withTimezone = date.toLocaleString(locale, { timeZoneName: 'short' });
    const withoutTimezone = date.toLocaleString(locale);
    return withTimezone.replace(withoutTimezone, '').trim();
  }

  private static timezoneOffset(date: Date): string {
    const offset = date.getTimezoneOffset() * -1;
    const hours = Math.abs(Math.floor(offset / 60));
    const minutes = offset % 60;
    const sign = offset >= 0 ? '+' : '-';
    return `${sign}${this.leftPad(hours.toString())}${this.leftPad(
      minutes.toString()
    )}`;
  }

  constructor(private readonly locale?: string) {}

  get directives(): string[] {
    return Object.keys(this.translations)
      .filter(key => key !== '%')
      .map(key => `%${key}`);
  }

  containsValidDirectives(pattern: string): boolean {
    this.regex.lastIndex = 0;
    const m = this.regex.exec(pattern);
    if (m === null) {
      return false;
    }
    const matches = m.find(value => this.directives.includes(value));
    return !!matches && matches.length > 0;
  }

  format(date: Date, format: string) {
    let formattedString = format;
    let m;

    const regex = this.regex;
    if (regex.lastIndex > 0) {
      regex.lastIndex = 0;
    }
    while ((m = regex.exec(format)) !== null) {
      if (m.index === regex.lastIndex) {
        regex.lastIndex++;
      }

      m.forEach(match => {
        const matched = match.slice(1);
        formattedString = formattedString.replace(
          match,
          this.translations[matched]?.(date, this.locale) || ''
        );
      });
    }
    return formattedString;
  }
}

export const displayDateFormatter = new DateFormatter();
