/**
 *
 * @param {number[]} numbers - Array of sorted numbers
 * @return {string} - Readable text of these sorted numbers
 * @example
 * groupConsecutiveNumbers([1, 2, 3, 5, 7, 10, 11, 12, 13]); // "1-3, 5, 7, 10-13"
 */

export function groupConsecutiveNumbers(numbers: number[]): string {
  if (numbers.length === 0)
    return '';

  const result: string[] = [];
  let start = numbers[0];
  let end = numbers[0];

  function pushGroup(): void {
    result.push(start === end ? start.toString() : `${start}-${end}`);
  }

  for (let i = 1; i < numbers.length; i++) {
    if (numbers[i] === end + 1) {
      end = numbers[i];
    }
    else {
      pushGroup();
      start = end = numbers[i];
    }
  }

  pushGroup();

  return result.join(', ');
}
