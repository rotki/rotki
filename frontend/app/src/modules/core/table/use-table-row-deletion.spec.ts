import { describe, expect, it, vi } from 'vitest';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';

interface Row {
  id: string;
}

function setup(deleteItem: (item: Row) => Promise<boolean>, onDeleted = vi.fn<(item: Row) => void>()): ReturnType<typeof useTableRowDeletion<Row>> & { onDeleted: typeof onDeleted } {
  return {
    ...useTableRowDeletion<Row>({
      deleteItem,
      failureTitle: item => `Could not delete ${item.id}`,
      onDeleted,
    }),
    onDeleted,
  };
}

describe('useTableRowDeletion', () => {
  it('should delete then run onDeleted, leaving no failure', async () => {
    const deleteItem = vi.fn<(item: Row) => Promise<boolean>>().mockResolvedValue(true);
    const { deleteRow, failure, onDeleted } = setup(deleteItem);

    await deleteRow({ id: 'a' });

    expect(deleteItem).toHaveBeenCalledWith({ id: 'a' });
    expect(onDeleted).toHaveBeenCalledWith({ id: 'a' });
    expect(get(failure)).toBeUndefined();
  });

  it('should not run onDeleted when the delete reports no removal', async () => {
    const { deleteRow, failure, onDeleted } = setup(vi.fn<(item: Row) => Promise<boolean>>().mockResolvedValue(false));

    await deleteRow({ id: 'a' });

    expect(onDeleted).not.toHaveBeenCalled();
    expect(get(failure)).toBeUndefined();
  });

  it('should keep a thrown delete as the failure, titled for its row', async () => {
    const error = new Error('boom');
    const { deleteRow, failure, onDeleted } = setup(vi.fn<(item: Row) => Promise<boolean>>().mockRejectedValue(error));

    await deleteRow({ id: 'a' });

    expect(get(failure)).toEqual({ failure: error, title: 'Could not delete a' });
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it('should drop the previous failure when the next delete starts', async () => {
    const deleteItem = vi.fn<(item: Row) => Promise<boolean>>()
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce(true);
    const { deleteRow, failure } = setup(deleteItem);

    await deleteRow({ id: 'a' });
    await deleteRow({ id: 'a' });

    expect(get(failure)).toBeUndefined();
  });
});
