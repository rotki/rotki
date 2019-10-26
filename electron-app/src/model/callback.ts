export interface Callback {
  id?: string;
  editfn?: ((row: DataTables.RowMethods) => void) | null;
  deletefn?: ((row: DataTables.RowMethods) => void) | null;
}
