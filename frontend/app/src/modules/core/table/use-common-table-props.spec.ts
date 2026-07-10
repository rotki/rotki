import { describe, expect, it } from 'vitest';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';

interface Row { id: number }

describe('useCommonTableProps', () => {
  it('should expose default table state refs', () => {
    const {
      confirmationMessage,
      editableItem,
      expanded,
      itemsToDelete,
      openDialog,
      selected,
    } = useCommonTableProps<Row>();

    expect(get(selected)).toEqual([]);
    expect(get(openDialog)).toBe(false);
    expect(get(editableItem)).toBeUndefined();
    expect(get(itemsToDelete)).toEqual([]);
    expect(get(confirmationMessage)).toBe('');
    expect(get(expanded)).toEqual([]);
  });

  it('should return independent state across instances', () => {
    const first = useCommonTableProps<Row>();
    const second = useCommonTableProps<Row>();

    set(first.selected, [{ id: 1 }]);
    set(first.openDialog, true);

    expect(get(second.selected)).toEqual([]);
    expect(get(second.openDialog)).toBe(false);
  });

  it('should allow updating the exposed refs', () => {
    const { confirmationMessage, editableItem, expanded } = useCommonTableProps<Row>();

    set(editableItem, { id: 7 });
    set(expanded, [{ id: 7 }]);
    set(confirmationMessage, 'delete?');

    expect(get(editableItem)).toEqual({ id: 7 });
    expect(get(expanded)).toEqual([{ id: 7 }]);
    expect(get(confirmationMessage)).toBe('delete?');
  });
});
