export interface TablePagination<T> {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof T)[];
  sortDesc: boolean[];
}
