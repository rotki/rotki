import { type Nullable } from '@rotki/common';

interface SplitResult {
  key: string;
  value: string;
  exclude?: boolean;
}

const defaultSplitResult = () => ({
  key: '',
  value: '',
  exclude: undefined
});

export const splitSearch = (keyword: Nullable<string>): SplitResult => {
  if (!keyword) {
    return defaultSplitResult();
  }
  const negateOperatorIndex = keyword.indexOf('!=');
  const equalOperatorIndex = Math.max(
    keyword.indexOf('='),
    keyword.indexOf(':')
  );

  const exclude = negateOperatorIndex > -1;

  if (!exclude && equalOperatorIndex < 0) {
    return {
      key: keyword.trim(),
      value: '',
      exclude: undefined
    };
  }

  const separatorIndex = exclude ? negateOperatorIndex : equalOperatorIndex;
  const length = exclude ? 2 : 1;

  const key = keyword.slice(0, Math.max(0, separatorIndex)).trim();
  const value = keyword
    .substring(separatorIndex + length, keyword.length)
    .trim();

  return {
    key,
    value,
    exclude
  };
};
