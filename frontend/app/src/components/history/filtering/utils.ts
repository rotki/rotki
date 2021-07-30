import { Nullable } from '@rotki/common';

export const splitSearch: (keyword: Nullable<string>) => string[] = (
  keyword: Nullable<string>
) => {
  if (!keyword) {
    return [];
  }
  return keyword.split(':').map(value => value.trim());
};
