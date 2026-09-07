import type { DataTableColumn } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { CustomAsset } from '@/modules/assets/types';
import { some } from 'es-toolkit/compat';

/** A custom asset shaped for `AssetDetailsBase`, which renders resolved and custom assets alike. */
interface CustomAssetDetails {
  customAssetType: string;
  identifier: string;
  isCustomAsset: true;
  name: string;
  symbol: string;
}

interface UseCustomAssetTableReturn {
  /** The table's columns. */
  cols: ComputedRef<DataTableColumn<CustomAsset>[]>;
  /**
   * Expands a row, or collapses it when it is already open.
   *
   * @remarks
   * Only one row is expanded at a time, so opening another closes the first.
   */
  expand: (item: CustomAsset) => void;
  /** Shapes a row for the shared asset display, which has no notion of a custom asset's fields. */
  getAsset: (item: CustomAsset) => CustomAssetDetails;
  /** Whether the row with this identifier is expanded. */
  isExpanded: (identifier: string) => boolean;
}

/**
 * The custom assets table's columns and its single-row expansion.
 *
 * @param expanded - the expanded rows, which this both reads and replaces
 * @returns the columns and the expansion helpers the rows bind
 */
export function useCustomAssetTable(expanded: Ref<CustomAsset[]>): UseCustomAssetTableReturn {
  const { t } = useI18n({ useScope: 'global' });

  const cols = computed<DataTableColumn<CustomAsset>[]>(() => [
    {
      cellClass: 'py-0',
      class: 'w-1/2',
      key: 'name',
      label: t('common.asset'),
      sortable: true,
    },
    {
      cellClass: 'py-0',
      class: 'w-1/2',
      key: 'custom_asset_type',
      label: t('common.type'),
      sortable: true,
    },
    {
      cellClass: 'py-0',
      key: 'actions',
      label: '',
    },
  ]);

  function getAsset(item: CustomAsset): CustomAssetDetails {
    return {
      customAssetType: item.customAssetType,
      identifier: item.identifier,
      isCustomAsset: true,
      name: item.name,
      symbol: item.customAssetType,
    };
  }

  function isExpanded(identifier: string): boolean {
    return some(get(expanded), { identifier });
  }

  function expand(item: CustomAsset): void {
    set(expanded, isExpanded(item.identifier) ? [] : [item]);
  }

  return {
    cols,
    expand,
    getAsset,
    isExpanded,
  };
}
