import type { Nullable } from '@rotki/common';

interface SplitResult {
  key: string;
  value: string;
  exclude?: boolean;
}

function defaultSplitResult(): SplitResult {
  return {
    exclude: undefined,
    key: '',
    value: '',
  };
}

export function splitSearch(keyword: Nullable<string>): SplitResult {
  if (!keyword)
    return defaultSplitResult();

  const negateOperatorIndex = keyword.indexOf('!=');
  const equalOperatorIndex = keyword.indexOf('=');
  const colonOperatorIndex = keyword.indexOf(':');
  const matchOperatorIndex
    = equalOperatorIndex === -1 || colonOperatorIndex === -1
      ? Math.max(equalOperatorIndex, colonOperatorIndex)
      : Math.min(equalOperatorIndex, colonOperatorIndex);

  const exclude = negateOperatorIndex > -1;

  if (!exclude && matchOperatorIndex < 0) {
    return {
      exclude: undefined,
      key: keyword.trim(),
      value: '',
    };
  }

  const separatorIndex = exclude ? negateOperatorIndex : matchOperatorIndex;
  const length = exclude ? 2 : 1;

  const key = keyword.slice(0, Math.max(0, separatorIndex)).trim();
  const value = keyword.substring(separatorIndex + length, keyword.length).trim();

  return {
    exclude,
    key,
    value,
  };
}
