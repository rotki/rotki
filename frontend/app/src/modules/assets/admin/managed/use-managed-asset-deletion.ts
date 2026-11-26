import type { SupportedAsset } from '@rotki/common';
import type { Ref } from 'vue';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { useI18n } from 'vue-i18n';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';

export interface UseManagedAssetDeletionReturn {
  /**
   * Deletes an asset the user already confirmed at its row.
   *
   * @remarks
   * A successful delete also drops the asset from the info cache, which otherwise keeps serving the
   * name and symbol of something that no longer exists.
   */
  deleteAsset: (item: SupportedAsset) => Promise<void>;
  /** What a row's delete button asks before deleting its asset. */
  deleteConfirm: (item: SupportedAsset) => RowDeleteQuestion;
  /** Why the last delete failed, named above the table. */
  deleteFailure: Readonly<Ref<NamedFailure | undefined>>;
}

/**
 * Deletes managed assets from their table rows, asking first and naming a failure.
 *
 * @param refetch - reloads the table's page after a successful delete
 */
export function useManagedAssetDeletion(refetch: () => Promise<void>): UseManagedAssetDeletionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { deleteAsset } = useAssetManagementApi();
  const { deleteCacheKey } = useAssetInfoCache();

  const deleteConfirm = (item: SupportedAsset): RowDeleteQuestion => ({
    message: t('asset_management.confirm_delete.message', { asset: item?.symbol ?? '' }),
    title: t('asset_management.confirm_delete.title'),
  });

  const { deleteRow, failure: deleteFailure } = useTableRowDeletion<SupportedAsset>({
    deleteItem: async item => deleteAsset(item.identifier),
    failureTitle: item => t('asset_management.delete_error', { address: item.identifier }),
    onDeleted: async (item) => {
      await refetch();
      deleteCacheKey(item.identifier);
    },
  });

  return {
    deleteAsset: deleteRow,
    deleteConfirm,
    deleteFailure,
  };
}
