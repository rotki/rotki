class MockFile {
  private readonly content: string;
  name: string;
  type: string;

  constructor(content: string[], filename: string, options: { type: string }) {
    this.content = content.join('\n');
    this.name = filename;
    this.type = options.type;
  }

  text(): string {
    return this.content;
  }
}

export function createMockCSV(content: string[]): File {
  return new MockFile(content, 'test.csv', { type: 'text/csv' }) as unknown as File;
}
