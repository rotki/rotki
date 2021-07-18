import { ManagedAsset } from '@/services/assets/types';

function levenshtein(a: string, b: string) {
  let tmp;
  if (a.length === 0) {
    return b.length;
  }
  if (b.length === 0) {
    return a.length;
  }
  if (a.length > b.length) {
    tmp = a;
    a = b;
    b = tmp;
  }

  let i: number,
    j: number,
    res: number = 0;
  const alen = a.length,
    blen = b.length,
    row = Array(alen);
  for (i = 0; i <= alen; i++) {
    row[i] = i;
  }

  for (i = 1; i <= blen; i++) {
    res = i;
    for (j = 1; j <= alen; j++) {
      tmp = row[j - 1];
      row[j - 1] = res;
      res =
        b[i - 1] === a[j - 1]
          ? tmp
          : Math.min(tmp + 1, Math.min(res + 1, row[j] + 1));
    }
  }
  return res;
}

function score(keyword: string, { name, symbol }: ManagedAsset): number {
  const symbolScore = levenshtein(keyword, symbol.toLocaleLowerCase());
  const nameScore = levenshtein(keyword, name.toLocaleLowerCase());
  return Math.min(symbolScore, nameScore);
}

export function compareAssets(
  a: ManagedAsset,
  b: ManagedAsset,
  element: keyof ManagedAsset,
  keyword: string,
  desc: boolean
): number {
  const fields = ['symbol', 'name'];
  if (keyword.length > 0 && fields.includes(element)) {
    const diff = score(keyword, a) - score(keyword, b);
    return desc ? diff * -1 : diff;
  }

  const aElement = a[element];
  const bElement = b[element];

  if (typeof bElement === 'number' && typeof aElement === 'number') {
    return desc ? bElement - aElement : aElement - bElement;
  } else if (typeof bElement === 'string' && typeof aElement === 'string') {
    return desc
      ? bElement.toLocaleLowerCase().localeCompare(aElement)
      : aElement.toLocaleLowerCase().localeCompare(bElement);
  }
  return 0;
}
