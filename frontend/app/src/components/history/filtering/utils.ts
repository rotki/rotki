import { Nullable } from '@rotki/common';
import { DateFormat } from '@/types/date-format';
import { convertToTimestamp } from '@/utils/date';

export const splitSearch: (keyword: Nullable<string>) => string[] = (
  keyword: Nullable<string>
) => {
  if (!keyword) {
    return [];
  }
  const key = keyword.split(':')[0];
  const value = keyword.replace(key + ':', '');

  return [key.trim(), value.trim()];
};

export const startMatch = (
  time: number,
  filter?: string,
  format: DateFormat = DateFormat.DateMonthYearHourMinuteSecond
) => {
  if (!filter) {
    return true;
  }
  const timestamp = convertToTimestamp(filter, format);
  return isNaN(timestamp) ? true : timestamp <= time;
};

export const endMatch = (
  time: number,
  filter?: string,
  format: DateFormat = DateFormat.DateMonthYearHourMinuteSecond
) => {
  if (!filter) {
    return true;
  }
  const timestamp = convertToTimestamp(filter, format);
  return isNaN(timestamp) ? true : timestamp >= time;
};

export const checkIfMatch = (value: string, keyword?: string) => {
  return keyword ? keyword === value : true;
};
