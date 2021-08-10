import { Nullable } from '@rotki/common';
import { convertToTimestamp } from '@/utils/date';

export const splitSearch: (keyword: Nullable<string>) => string[] = (
  keyword: Nullable<string>
) => {
  if (!keyword) {
    return [];
  }
  return keyword.split(':').map(value => value.trim());
};

export const startMatch = (time: number, filter?: string) => {
  if (!filter) {
    return true;
  }
  const timestamp = convertToTimestamp(filter);
  return isNaN(timestamp) ? true : timestamp <= time;
};

export const endMatch = (time: number, filter?: string) => {
  if (!filter) {
    return true;
  }
  const timestamp = convertToTimestamp(filter);
  return isNaN(timestamp) ? true : timestamp >= time;
};

export const checkIfMatch = (value: string, keyword?: string) => {
  return keyword ? keyword === value : true;
};
