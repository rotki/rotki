import type { DataTableSortData } from '@rotki/ui-library';
import { get, set } from '@vueuse/shared';
import { describe, expect, it, vi } from 'vitest';
import { useTableSorting } from '@/modules/core/table/use-table-sorting';

interface Row {
  timestamp: number;
  amount: number;
}

describe('useTableSorting', () => {
  it('should seed the internal sorting from the provided default', () => {
    const { internalSorting } = useTableSorting<Row>(
      { column: 'amount', direction: 'asc' },
      vi.fn(),
    );
    expect(get(internalSorting)).toStrictEqual({ column: 'amount', direction: 'asc' });
  });

  it('should fall back to the fallback column and desc when no default is given', () => {
    const { internalSorting } = useTableSorting<Row>(undefined, vi.fn(), 'timestamp');
    expect(get(internalSorting)).toStrictEqual({ column: 'timestamp', direction: 'desc' });
  });

  it('should hand out a fresh default object on each call', () => {
    const { defaultSorting } = useTableSorting<Row>({ column: 'amount', direction: 'asc' }, vi.fn());
    expect(defaultSorting()).not.toBe(defaultSorting());
    expect(defaultSorting()).toStrictEqual(defaultSorting());
  });

  it('should read the current sorting through the model', () => {
    const { internalSorting, sort } = useTableSorting<Row>({ column: 'amount', direction: 'desc' }, vi.fn());
    expect(get(sort)).toBe(get(internalSorting));
  });

  it('should commit a normalized single-column sort on write', () => {
    const commitSort = vi.fn();
    const { sort } = useTableSorting<Row>({ column: 'timestamp', direction: 'desc' }, commitSort);
    set(sort, { column: 'amount', direction: 'asc' });
    expect(commitSort).toHaveBeenCalledWith({ column: 'amount', direction: 'asc' });
  });

  it('should commit an array sort as-is without normalizing', () => {
    const commitSort = vi.fn();
    const { sort } = useTableSorting<Row>({ column: 'timestamp', direction: 'desc' }, commitSort);
    const arraySort: DataTableSortData<Row> = [{ column: 'amount', direction: 'asc' }];
    set(sort, arraySort);
    expect(commitSort).toHaveBeenCalledWith(arraySort);
  });

  it('should commit an undefined sort without normalizing', () => {
    const commitSort = vi.fn();
    const { sort } = useTableSorting<Row>({ column: 'timestamp', direction: 'desc' }, commitSort);
    set(sort, undefined);
    expect(commitSort).toHaveBeenCalledWith(undefined);
  });
});
