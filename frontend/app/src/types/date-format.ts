import { z } from 'zod';

export enum DateFormat {
  DateMonthYearHourMinuteSecondTimezone = '%d/%m/%Y %H:%M:%S %Z',
  DateMonthYearHourMinuteSecond = '%d/%m/%Y %H:%M:%S',
  MonthDateYearHourMinuteSecond = '%m/%d/%Y %H:%M:%S',
  YearMonthDateHourMinuteSecond = '%Y/%m/%d %H:%M:%S'
}

export const DateFormatEnum = z.nativeEnum(DateFormat);
