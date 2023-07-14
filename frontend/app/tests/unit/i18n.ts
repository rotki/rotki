function stringify(value: Record<string, any>): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

export const mockT = (key: any, args?: any) =>
  args ? `${key}::${stringify(args)}` : key;
