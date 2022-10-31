export interface TabContent {
  readonly text: string;
  readonly route: string;
  readonly hidden?: boolean;
  readonly hideHeader?: boolean;
}

export const getClass = (route: string) => {
  return route.toLowerCase().replace('/', '').replace(/\//g, '__');
};
