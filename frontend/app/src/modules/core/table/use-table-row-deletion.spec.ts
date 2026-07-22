import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';

/** The confirm callback shape the store's `show` receives. */
type OnConfirm = () => void | Promise<void>;

const show = vi.fn();
const setMessage = vi.fn();

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: typeof show } => ({ show }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): { setMessage: typeof setMessage } => ({ setMessage }),
}));

interface Row {
  id: string;
}

/** The onConfirm callback the composable handed to `show`. */
function capturedOnConfirm(): OnConfirm {
  return show.mock.calls[0][1];
}

describe('useTableRowDeletion', () => {
  beforeEach((): void => {
    vi.clearAllMocks();
  });

  it('should open the confirm dialog with the row copy', (): void => {
    const { showDeleteConfirmation } = useTableRowDeletion<Row>({
      confirm: (item): { message: string; title: string } => ({ message: `delete ${item.id}`, title: 'Confirm' }),
      deleteItem: vi.fn().mockResolvedValue(true),
    });

    showDeleteConfirmation({ id: 'a' });

    expect(show).toHaveBeenCalledWith({ message: 'delete a', title: 'Confirm' }, expect.any(Function));
  });

  it('should delete then run onDeleted when confirmed', async (): Promise<void> => {
    const deleteItem = vi.fn().mockResolvedValue(true);
    const onDeleted = vi.fn();
    const { showDeleteConfirmation } = useTableRowDeletion<Row>({
      confirm: (): { message: string; title: string } => ({ message: 'm', title: 't' }),
      deleteItem,
      onDeleted,
    });

    showDeleteConfirmation({ id: 'a' });
    await capturedOnConfirm()();

    expect(deleteItem).toHaveBeenCalledWith({ id: 'a' });
    expect(onDeleted).toHaveBeenCalledWith({ id: 'a' });
  });

  it('should not run onDeleted when the delete reports no removal', async (): Promise<void> => {
    const onDeleted = vi.fn();
    const { showDeleteConfirmation } = useTableRowDeletion<Row>({
      confirm: (): { message: string; title: string } => ({ message: 'm', title: 't' }),
      deleteItem: vi.fn().mockResolvedValue(false),
      onDeleted,
    });

    showDeleteConfirmation({ id: 'a' });
    await capturedOnConfirm()();

    expect(onDeleted).not.toHaveBeenCalled();
    expect(setMessage).not.toHaveBeenCalled();
  });

  it('should toast the custom error message when the delete throws', async (): Promise<void> => {
    const { showDeleteConfirmation } = useTableRowDeletion<Row>({
      confirm: (): { message: string; title: string } => ({ message: 'm', title: 't' }),
      deleteItem: vi.fn().mockRejectedValue(new Error('boom')),
      errorMessage: (item, error): string => `failed ${item.id}: ${error instanceof Error ? error.message : String(error)}`,
    });

    showDeleteConfirmation({ id: 'a' });
    await capturedOnConfirm()();

    expect(setMessage).toHaveBeenCalledWith({ description: 'failed a: boom' });
  });

  it('should fall back to the raw error message when none is provided', async (): Promise<void> => {
    const { showDeleteConfirmation } = useTableRowDeletion<Row>({
      confirm: (): { message: string; title: string } => ({ message: 'm', title: 't' }),
      deleteItem: vi.fn().mockRejectedValue(new Error('raw')),
    });

    showDeleteConfirmation({ id: 'a' });
    await capturedOnConfirm()();

    expect(setMessage).toHaveBeenCalledWith({ description: 'raw' });
  });
});
