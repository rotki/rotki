import type { Ref } from 'vue';

/** The question the row's delete button asks, beside it, before deleting. */
interface RowDeletionConfirmation {
  title: string;
  message: string;
}

/** A delete that failed, named above the table it was made from. */
interface RowDeletionFailure {
  title: string;
  error: unknown;
}

interface UseTableRowDeletionOptions<T> {
  /** Performs the delete. Resolves `true` when the row was actually removed. */
  deleteItem: (item: T) => Promise<boolean>;
  /** What the delete button asks for this row. */
  confirm: (item: T) => RowDeletionConfirmation;
  /** Runs after a successful delete, e.g. refetch the table and purge caches. */
  onDeleted?: (item: T) => void | Promise<void>;
  /** The strip's title when deleting this row fails; the strip words the error itself. */
  failureTitle: (item: T) => string;
}

interface UseTableRowDeletionReturn<T> {
  /** For `RowActions`' `delete-confirm`, so the button asks before it emits. */
  deleteConfirm: (item: T) => RowDeletionConfirmation;
  /** Deletes a row the user already confirmed. */
  deleteRow: (item: T) => Promise<void>;
  /** Why the last delete failed, until the next one starts. */
  failure: Readonly<Ref<RowDeletionFailure | undefined>>;
}

/**
 * The delete-a-row flow the admin tables share: the row's button asks beside it, the delete runs,
 * then the table refetches on success or names the failure above its rows.
 *
 * @remarks
 * The row stays when the delete fails, so its delete button is the retry and the strip offers none.
 */
export function useTableRowDeletion<T>(
  options: UseTableRowDeletionOptions<T>,
): UseTableRowDeletionReturn<T> {
  const { confirm, deleteItem, failureTitle, onDeleted } = options;
  const failure = shallowRef<RowDeletionFailure>();

  async function deleteRow(item: T): Promise<void> {
    set(failure, undefined);
    try {
      if (await deleteItem(item))
        await onDeleted?.(item);
    }
    catch (error: unknown) {
      set(failure, { error, title: failureTitle(item) });
    }
  }

  return {
    deleteConfirm: confirm,
    deleteRow,
    failure: readonly(failure),
  };
}
