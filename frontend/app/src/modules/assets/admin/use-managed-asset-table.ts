import type { SupportedAsset } from '@rotki/common';
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { some } from 'es-toolkit/compat';
import { EVM_TOKEN, isSpammableAssetType, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useSetting } from '@/modules/settings/use-setting';

interface UseManagedAssetTableReturn {
  cols: ComputedRef<DataTableColumn<SupportedAsset>[]>;
  data: ComputedRef<SupportedAsset[]>;
  expand: (item: SupportedAsset) => void;
  /**
   * The chain whose explorer can show this asset, when one can.
   *
   * @remarks
   * Hyperliquid Core tokens have none: their ids are not HyperEVM addresses, so no explorer would
   * resolve them. Their icon comes from the resolved asset type instead, so nothing is lost.
   */
  getAssetLocation: (row: SupportedAsset) => string | undefined;
  isExpanded: (identifier: string) => boolean;
  /**
   * Whether marking the selection as spam is unavailable.
   *
   * @remarks
   * The action stays available while nothing is selected, because the button is what the user
   * reaches for first. Once there is a selection it is only offered when at least one of the
   * selected assets is of a type that can be spam.
   */
  spamDisabled: ComputedRef<boolean>;
}

export function useManagedAssetTable(
  paginationModel: Ref<TablePaginationData>,
  expanded: Ref<SupportedAsset[]>,
  collection: MaybeRefOrGetter<Collection<SupportedAsset>>,
  selected: MaybeRefOrGetter<string[]>,
): UseManagedAssetTableReturn {
  const { t } = useI18n({ useScope: 'global' });
  const itemsPerPage = useSetting('itemsPerPage');

  const cols = computed<DataTableColumn<SupportedAsset>[]>(() => [{
    cellClass: 'py-0',
    class: 'w-full',
    key: 'symbol',
    label: t('common.asset'),
    sortable: true,
  }, {
    cellClass: '!text-nowrap py-0',
    key: 'type',
    label: t('common.type'),
    sortable: true,
  }, {
    cellClass: 'py-0',
    class: 'min-w-[11.375rem]',
    key: 'address',
    label: t('common.address'),
    sortable: true,
  }, {
    cellClass: 'py-0',
    class: 'min-w-[10rem]',
    key: 'started',
    label: t('asset_table.headers.started'),
    sortable: true,
  }, {
    cellClass: 'py-0',
    key: 'ignored',
    label: t('assets.action.ignore'),
  }, {
    key: 'actions',
    label: '',
  }]);

  const data = computed<SupportedAsset[]>(() => toValue(collection).data ?? []);
  const found = computed<number>(() => toValue(collection).found ?? 0);

  const setPage = (page: number): void => {
    set(paginationModel, {
      ...get(paginationModel),
      page,
    });
  };

  const isExpanded = (identifier: string): boolean => some(get(expanded), { identifier });

  const expand = (item: SupportedAsset): void => {
    set(expanded, isExpanded(item.identifier) ? [] : [item]);
  };

  watch([data, found, itemsPerPage], ([data, found, itemsPerPage]) => {
    if (data.length === 0 && found > 0) {
      const lastPage = Math.ceil(found / itemsPerPage);
      setPage(lastPage);
    }
  });

  const spamDisabled = computed<boolean>(() => {
    const selectedIds = toValue(selected);
    if (selectedIds.length === 0)
      return false;

    const assets = get(data);
    return !selectedIds.some((id) => {
      const asset = assets.find(item => item.identifier === id);
      return asset && isSpammableAssetType(asset.assetType);
    });
  });

  function getAssetLocation(row: SupportedAsset): string | undefined {
    if (row.assetType === EVM_TOKEN)
      return row.evmChain ?? undefined;

    if (row.assetType === SOLANA_TOKEN)
      return SOLANA_CHAIN;

    return undefined;
  }

  return {
    cols,
    data,
    expand,
    getAssetLocation,
    isExpanded,
    spamDisabled,
  };
}
