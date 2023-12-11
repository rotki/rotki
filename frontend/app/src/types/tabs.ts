export interface TabContent {
  readonly text: string;
  readonly icon: string;
  readonly route: string;
}

export const getClass = (route: string): string =>
  route.toLowerCase().replace('/', '').replace(/\//g, '__');
