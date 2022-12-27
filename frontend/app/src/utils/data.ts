export function chunkArray<T>(myArray: T[], size: number): T[][] {
  const results: T[][] = [];

  while (myArray.length > 0) {
    results.push(myArray.splice(0, size));
  }

  return results;
}

export const uniqueStrings = function <T = string>(
  value: T,
  index: number,
  array: T[]
): boolean {
  return array.indexOf(value) === index;
};

export function nonNullProperties<T extends object>(object: T): Partial<T> {
  const partial: Partial<T> = {};
  const keys = Object.keys(object);
  for (const obKey of keys) {
    const key = obKey as keyof T;
    if (object[key] === null) {
      continue;
    }
    partial[key] = object[key];
  }
  return partial;
}

export const size = (bytes: number): string => {
  let i = 0;

  for (i; bytes > 1024; i++) {
    bytes /= 1024;
  }

  const symbol = 'KMGTPEZY'[i - 1] || '';
  return `${bytes.toFixed(2)}  ${symbol}B`;
};

export function randomHex(characters = 40): string {
  let hex = '';
  for (let i = 0; i < characters - 2; i++) {
    const randByte = Number.parseInt(
      (Math.random() * 16).toString(),
      10
    ).toString(16);
    hex += randByte;
  }
  return `0x${hex}ff`;
}

export function emptyArrayToNull<T>(data: T | null): T | null {
  if (Array.isArray(data) && data.length === 0) return null;

  return data;
}
