export interface PaginationRequestPayload<T> {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttributes?: (keyof T)[];
  readonly ascending?: boolean[];
  readonly ignoreCache?: boolean;
  readonly onlyCache?: boolean;
}
