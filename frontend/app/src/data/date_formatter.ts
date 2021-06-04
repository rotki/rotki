export class DateFormatter {
  private regex = /%-?[a-zA-Z]/gm;
  private translations: {
    [directive: string]: (date: Date, locale: string) => string;
  } = {
    a: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { weekday: 'short' }),
    A: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { weekday: 'long' }),
    w: (date: Date) => date.getDay().toString(),
    y: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { year: '2-digit' }),
    Y: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { year: 'numeric' }),
    b: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { month: 'short' }),
    B: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { month: 'long' }),
    m: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { month: '2-digit' }),
    '-m': (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { month: 'numeric' }),
    d: (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { day: '2-digit' }),
    '-d': (date: Date, locale: string) =>
      date.toLocaleDateString(locale, { day: 'numeric' }),
    H: (date: Date) => DateFormatter.leftPad(date.getHours().toString()),
    '-H': (date: Date) => date.getHours().toString(),
    I: (date: Date) => DateFormatter.leftPad(DateFormatter.twelveHours(date)),
    '-I': (date: Date) => DateFormatter.twelveHours(date),
    M: (date: Date) => DateFormatter.leftPad(date.getMinutes().toString()),
    '-M': (date: Date) => date.getMinutes().toString(),
    S: (date: Date) => DateFormatter.leftPad(date.getSeconds().toString()),
    '-S': (date: Date) => date.getSeconds().toString(),
    p: (date, locale) => DateFormatter.amPm(date, locale),
    z: (date: Date) => DateFormatter.timezoneOffset(date),
    Z: (date: Date, locale: string) => DateFormatter.timezone(date, locale),
    j: (date: Date) =>
      DateFormatter.leftPad(DateFormatter.dayOfTheYear(date).toString(), 3),
    '-j': (date: Date) => DateFormatter.dayOfTheYear(date).toString(),
    c: (date: Date, locale: string) => date.toLocaleString(locale),
    x: (date: Date, locale: string) => date.toLocaleDateString(locale),
    X: (date: Date, locale: string) => date.toLocaleTimeString(locale),
    '%': () => '%'
  };

  private static leftPad(
    text: string,
    length: number = 2,
    padString: string = '0'
  ): string {
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

  private static amPm(date: Date, locale: string): string {
    const timeString = date.toLocaleTimeString(locale, { hour12: true });
    return timeString.substr(timeString.length - 2);
  }

  private static timezone(date: Date, locale: string): string {
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

  constructor(private readonly locale: string = 'en-US') {}

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
        const matched = match.substr(1);
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
