import { _adapters, type TimeUnit } from 'chart.js';
import dayjs, { type QUnitType } from 'dayjs';
import AdvancedFormat from 'dayjs/plugin/advancedFormat';
import CustomParseFormat from 'dayjs/plugin/customParseFormat';
import isoWeek from 'dayjs/plugin/isoWeek';
import LocalizedFormat from 'dayjs/plugin/localizedFormat';
import QuarterOfYear from 'dayjs/plugin/quarterOfYear';

dayjs.extend(AdvancedFormat);
dayjs.extend(QuarterOfYear);
dayjs.extend(LocalizedFormat);
dayjs.extend(CustomParseFormat);
dayjs.extend(isoWeek);

const FORMATS = {
  datetime: 'MMM D, YYYY, h:mm:ss a',
  day: 'MMM D',
  hour: 'hA',
  millisecond: 'h:mm:ss.SSS a',
  minute: 'h:mm a',
  month: 'MMM YYYY',
  quarter: '[Q]Q - YYYY',
  second: 'h:mm:ss a',
  week: 'll',
  year: 'YYYY',
};

_adapters._date.override({
  add(time: any, amount: number, unit: QUnitType & TimeUnit) {
    return dayjs(time).add(amount, unit).valueOf();
  },
  diff(max: any, min: any, unit: TimeUnit) {
    return dayjs(max).diff(dayjs(min), unit);
  },
  endOf(time: any, unit: TimeUnit & QUnitType) {
    return dayjs(time).endOf(unit).valueOf();
  },
  format(time: any, format: TimeUnit): string {
    return dayjs(time).format(format);
  },
  formats: () => FORMATS,
  parse(value: any, format?: TimeUnit) {
    const valueType = typeof value;

    if (value === null || valueType === 'undefined')
      return null;

    if (valueType === 'string' && typeof format === 'string')
      return dayjs(value, format).isValid() ? dayjs(value, format).valueOf() : null;
    else if (!(value instanceof dayjs))
      return dayjs(value).isValid() ? dayjs(value).valueOf() : null;

    return null;
  },
  startOf(time: any, unit: (TimeUnit & QUnitType) | 'isoWeek', weekday?: number) {
    if (unit === 'isoWeek') {
      // Ensure that weekday has a valid format
      const validatedWeekday: number = typeof weekday === 'number' && weekday > 0 && weekday < 7 ? weekday : 1;
      return dayjs(time).isoWeekday(validatedWeekday).startOf('day').valueOf();
    }
    return dayjs(time).startOf(unit).valueOf();
  },
});
