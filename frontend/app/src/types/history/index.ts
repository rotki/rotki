export type HistoryRequestPayload<T> = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttributes?: (keyof T)[];
  readonly ascending: boolean[];
  readonly onlyCache?: boolean;
};
