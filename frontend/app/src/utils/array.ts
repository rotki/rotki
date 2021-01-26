export function chunkArray<T>(myArray: T[], size: number): T[][] {
  const results: T[][] = [];

  while (myArray.length) {
    results.push(myArray.splice(0, size));
  }

  return results;
}
