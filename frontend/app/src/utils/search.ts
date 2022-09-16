import { Nullable } from '@rotki/common';

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
