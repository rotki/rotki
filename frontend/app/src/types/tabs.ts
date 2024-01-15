export interface TabContent {
  readonly text: string;
  readonly icon: string;
  readonly route: string;
}

export function getClass(route: string): string {
  return route.toLowerCase().replace('/', '').replace(/\//g, '__');
}
