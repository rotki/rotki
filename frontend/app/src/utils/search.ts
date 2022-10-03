import { Nullable } from '@rotki/common';

export const splitSearch: (keyword: Nullable<string>) => string[] = (
  keyword: Nullable<string>
) => {
  if (!keyword) {
    return [];
  }
  const index = keyword.indexOf(':');
  if (index < 0) {
    return [keyword.trim(), ''];
  }

  const key = keyword.substring(0, index).trim();
  const value = keyword.substring(index + 1, keyword.length).trim();
  return [key, value];
};
