import { pslSuffixes } from '@/data/psl';

export const getDomain = (str: string): string => {
  const pattern = /^(?:https?:)?(?:\/\/)?(?:[^\n@]+@)?(?:www\.)?([^\n/:]+)/;
  const exec = pattern.exec(str);

  const withSubdomain = exec?.[1];

  if (!withSubdomain) {
    return str;
  }

  const parts = withSubdomain.split('.');
  const length = parts.length;
  let i = length - 1;
  let domain = withSubdomain;

  while (i > 0) {
    const used = parts.slice(-i).join('.');
    const found = pslSuffixes.has(used);

    if (found) {
      break;
    }

    domain = used;
    i -= 1;
  }

  return domain;
};
