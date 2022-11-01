function stringify(value: { [key: string]: any }): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

export const mockT = (key: any, args?: any) =>
  args ? `${key}::${stringify(args)}` : key;

export const mockTc = (key: string, choice?: number, args?: object) =>
  args ? `${key}::${choice}::${stringify(args)}` : key;
