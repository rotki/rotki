function stringify(value: Record<string, any>): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

export function mockT(key: any, args?: any) {
  return args ? `${key}::${stringify(args)}` : key;
}
