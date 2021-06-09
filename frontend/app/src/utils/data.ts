export function chunkArray<T>(myArray: T[], size: number): T[][] {
  const results: T[][] = [];

  while (myArray.length) {
    results.push(myArray.splice(0, size));
  }

  return results;
}

export const uniqueStrings = function (
  value: string,
  index: number,
  array: string[]
): boolean {
  return array.indexOf(value) === index;
};

export function nonNullProperties<T>(object: T): Partial<T> {
  const partial: Partial<T> = {};
  const keys = Object.keys(object);
  for (let i = 0; i < keys.length; i++) {
    const key = keys[i] as keyof T;
    if (object[key] === null) {
      continue;
    }
    partial[key] = object[key];
  }
  return partial;
}
