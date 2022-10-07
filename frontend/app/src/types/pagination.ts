export interface TablePagination<T> {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof T)[];
  sortDesc: boolean[];
}

export interface ApiPagination<T> {
  limit: number;
  offset: number;
  orderByAttributes: (keyof T)[];
  ascending: boolean[];
}

export const convertPagination = <T>(
  { itemsPerPage, page, sortBy, sortDesc }: TablePagination<T>,
  defaultOrder: keyof T
): ApiPagination<T> => ({
  limit: itemsPerPage,
  offset: (page - 1) * itemsPerPage,
  orderByAttributes: sortBy.length > 0 ? sortBy : [defaultOrder],
  ascending: sortDesc.map(bool => !bool)
});
