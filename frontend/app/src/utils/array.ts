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
