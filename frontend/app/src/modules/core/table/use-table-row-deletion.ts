import type { Ref } from 'vue';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

interface UseTableRowDeletionOptions<T> {
  /** Performs the delete. Resolves `true` when the row was actually removed. */
  deleteItem: (item: T) => Promise<boolean>;
  /** Runs after a successful delete, e.g. refetch the table and purge caches. */
  onDeleted?: (item: T) => void | Promise<void>;
  /** The strip's title when deleting this row fails; the strip words the error itself. */
  failureTitle: (item: T) => string;
}

interface UseTableRowDeletionReturn<T> {
  /** Deletes a row the user already confirmed. */
  deleteRow: (item: T) => Promise<void>;
  /** Why the last delete failed, until the next one starts. */
  failure: Readonly<Ref<NamedFailure | undefined>>;
}

/**
 * The delete-a-row flow the admin tables share: the delete runs, then the table refetches on
 * success or names the failure above its rows.
 *
 * @remarks
 * Only a row the user already confirmed reaches `deleteRow`: the caller words the question its
 * row's delete button asks (`RowActions`' `delete-confirm`), since this flow never reads it. The
 * row stays when the delete fails, so its delete button is the retry and the strip offers none.
 */
export function useTableRowDeletion<T>(
  options: UseTableRowDeletionOptions<T>,
): UseTableRowDeletionReturn<T> {
  const { deleteItem, failureTitle, onDeleted } = options;
  const { failure, run } = useFailureSlot();

  async function deleteRow(item: T): Promise<void> {
    await run(failureTitle(item), async () => {
      if (await deleteItem(item))
        await onDeleted?.(item);
    });
  }

  return {
    deleteRow,
    failure,
  };
}
