export function createMockCSV(content: string[]): File {
  return new File([content.join('\n')], 'test.csv', { type: 'text/csv' });
}
