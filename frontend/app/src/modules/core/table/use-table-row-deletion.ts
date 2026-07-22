import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';

/** The confirm-dialog copy for the row being deleted. */
interface RowDeletionConfirmation {
  title: string;
  message: string;
}

interface UseTableRowDeletionOptions<T> {
  /** Performs the delete. Resolves `true` when the row was actually removed. */
  deleteItem: (item: T) => Promise<boolean>;
  /** The confirmation dialog copy for the row being deleted. */
  confirm: (item: T) => RowDeletionConfirmation;
  /** Runs after a successful delete, e.g. refetch the table and purge caches. */
  onDeleted?: (item: T) => void | Promise<void>;
  /**
   * The toast description shown when the delete throws. Each table phrases this
   * differently, so it is a param; without one the raw error message is used.
   */
  errorMessage?: (item: T, error: unknown) => string;
}

interface UseTableRowDeletionReturn<T> {
  /** Opens the confirm dialog, deletes on confirm, and toasts on failure. */
  showDeleteConfirmation: (item: T) => void;
}

/**
 * The delete-a-row flow the asset-admin tables share: confirm, delete, then refetch
 * on success or toast on failure. Only the delete call, the dialog copy and the
 * post-delete step vary per table, so those are the params; the control flow - which
 * was copy-pasted across the mapping and asset content components - lives here once.
 */
export function useTableRowDeletion<T>(
  options: UseTableRowDeletionOptions<T>,
): UseTableRowDeletionReturn<T> {
  const { confirm, deleteItem, errorMessage, onDeleted } = options;
  const { show } = useConfirmStore();
  const { setMessage } = useMessageStore();

  function showDeleteConfirmation(item: T): void {
    show(confirm(item), async (): Promise<void> => {
      try {
        const success = await deleteItem(item);
        if (success)
          await onDeleted?.(item);
      }
      catch (error: unknown) {
        setMessage({
          description: errorMessage ? errorMessage(item, error) : getErrorMessage(error),
        });
      }
    });
  }

  return { showDeleteConfirmation };
}
