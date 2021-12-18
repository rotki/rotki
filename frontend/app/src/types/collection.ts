export interface Collection<T> {
  data: T[];
  limit: number;
  found: number;
  total: number;
}

export interface CollectionResponse<T> {
  entries: T[];
  entriesFound: number;
  entriesLimit: number;
  entriesTotal: number;
}
