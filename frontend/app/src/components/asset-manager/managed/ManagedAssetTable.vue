<script setup lang="ts">
import { some } from 'lodash-es';
import {
  CUSTOM_ASSET,
  EVM_TOKEN,
  IgnoredAssetHandlingType,
  type IgnoredAssetsHandlingType,
} from '@/types/asset';
import type { Collection } from '@/types/collection';
import type { Filters, Matcher } from '@/composables/filters/assets';
import type {
  DataTableColumn,
  DataTableSortData,
  TablePaginationData,
} from '@rotki/ui-library-compat';
import type { SupportedAsset } from '@rotki/common/lib/data';
import type { ActionStatus } from '@/types/action';

const props = withDefaults(
  defineProps<{
    collection: Collection<SupportedAsset>;
    matchers: Matcher[];
    filters: Filters;
    pagination: TablePaginationData;
    sort: DataTableSortData;
    expanded: SupportedAsset[];
    selected: string[];
    ignoredAssets: string[];
    ignoredFilter: {
      onlyShowOwned: boolean;
      onlyShowWhitelisted: boolean;
      ignoredAssetsHandling: IgnoredAssetsHandlingType;
    };

    loading?: boolean;
  }>(),
  { loading: false },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
  (e: 'edit', asset: SupportedAsset): void;
  (e: 'delete-asset', asset: SupportedAsset): void;
  (e: 'update:filters', filters: Filters): void;
  (e: 'update:selected', selectedAssets: string[]): void;
  (e: 'update:expanded', expandedAssets: SupportedAsset[]): void;
  (e: 'update:pagination', pagination: TablePaginationData): void;
  (e: 'update:sort', sort: DataTableSortData): void;
  (
    e: 'update:ignored-filter',
    value: {
      onlyShowOwned: boolean;
      onlyShowWhitelisted: boolean;
      ignoredAssetsHandling: IgnoredAssetsHandlingType;
    }
  ): void;
}>();

const { t } = useI18n();

const paginationModel = useVModel(props, 'pagination', emit);
const sortModel = useVModel(props, 'sort', emit);

const cols = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset'),
    key: 'symbol',
    sortable: true,
    class: 'w-full',
    cellClass: 'py-0',
  },
  {
    label: t('common.type'),
    key: 'type',
    sortable: true,
    cellClass: '!text-nowrap py-0',
  },
  {
    label: t('common.address'),
    key: 'address',
    sortable: true,
    class: 'min-w-[11.375rem]',
    cellClass: 'py-0',
  },
  {
    label: t('asset_table.headers.started'),
    key: 'started',
    sortable: true,
    class: 'min-w-[10rem]',
    cellClass: 'py-0',
  },
  {
    label: t('assets.ignore'),
    key: 'ignored',
    cellClass: 'py-0',
  },
  {
    label: '',
    key: 'actions',
  },
]);

const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

const updateFilter = (filters: Filters) => emit('update:filters', filters);

function updateSelected(selectedAssets: string[]) {
  emit('update:selected', selectedAssets);
}

function updateExpanded(expandedAssets: SupportedAsset[]) {
  return emit('update:expanded', expandedAssets);
}

const ignoredFilter = useKebabVModel(props, 'ignoredFilter', emit);

const disabledIgnoreActions = computed(() => {
  const { ignoredAssetsHandling } = get(ignoredFilter);
  return ({
    ignore: ignoredAssetsHandling === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: ignoredAssetsHandling === IgnoredAssetHandlingType.EXCLUDE,
  });
});

const formatType = (string?: string) => toSentenceCase(string ?? 'EVM token');

function getAsset(item: SupportedAsset) {
  const name
    = item.name
    ?? item.symbol
    ?? (isEvmIdentifier(item.identifier)
      ? getAddressFromEvmIdentifier(item.identifier)
      : item.identifier);

  return {
    name,
    symbol: item.symbol ?? '',
    identifier: item.identifier,
    isCustomAsset: item.assetType === CUSTOM_ASSET,
    customAssetType: item.customAssetType ?? '',
  };
}

const { setMessage } = useMessageStore();
const { isAssetIgnored, ignoreAsset, unignoreAsset, fetchIgnoredAssets } = useIgnoredAssetsStore();
const { isAssetWhitelisted, whitelistAsset, unWhitelistAsset } = useWhitelistedAssetsStore();

const { markAssetAsSpam, removeAssetFromSpamList } = useSpamAsset();

function isAssetWhitelistedValue(asset: string) {
  return get(isAssetWhitelisted(asset));
}

const { getChain } = useSupportedChains();

async function toggleIgnoreAsset(identifier: string) {
  if (get(isAssetIgnored(identifier)))
    await unignoreAsset(identifier);
  else
    await ignoreAsset(identifier);

  if (props.ignoredFilter.ignoredAssetsHandling !== 'none')
    emit('refresh');
}

const isSpamAsset = (asset: SupportedAsset) => asset.protocol === 'spam';

async function toggleSpam(item: SupportedAsset) {
  const { identifier } = item;
  if (isSpamAsset(item))
    await removeAssetFromSpamList(identifier);
  else
    await markAssetAsSpam(identifier);

  emit('refresh');
}

async function toggleWhitelistAsset(identifier: string) {
  if (get(isAssetWhitelisted(identifier)))
    await unWhitelistAsset(identifier);
  else
    await whitelistAsset(identifier);

  emit('refresh');
}

async function massIgnore(ignored: boolean) {
  const ids = get(props.selected)
    .filter((identifier) => {
      const isItemIgnored = get(isAssetIgnored(identifier));
      return ignored ? !isItemIgnored : isItemIgnored;
    })
    .filter(uniqueStrings);

  let status: ActionStatus;

  if (ids.length === 0) {
    const choice = ignored ? 1 : 2;
    setMessage({
      success: false,
      title: t('ignore.no_items.title', choice),
      description: t('ignore.no_items.description', choice),
    });
    return;
  }

  if (ignored)
    status = await ignoreAsset(ids);
  else
    status = await unignoreAsset(ids);

  if (status.success) {
    updateSelected([]);
    if (props.ignoredFilter.ignoredAssetsHandling !== 'none')
      emit('refresh');
  }
}

function isExpanded(identifier: string) {
  return some(props.expanded, { identifier });
}

function expand(item: SupportedAsset) {
  updateExpanded(isExpanded(item.identifier) ? [] : [item]);
}

function setPage(page: number) {
  set(paginationModel, {
    ...get(paginationModel),
    page,
  });
}
</script>

<template>
  <div data-cy="managed-assets-table">
    <div class="flex flex-row flex-wrap items-center gap-2 mb-4">
      <div class="flex flex-row gap-2">
        <IgnoreButtons
          :disabled="selected.length === 0"
          :disabled-actions="disabledIgnoreActions"
          @ignore="massIgnore($event)"
        />
        <div
          v-if="selected.length > 0"
          class="flex flex-row items-center gap-2"
        >
          {{ t('asset_table.selected', { count: selected.length }) }}
          <RuiButton
            size="sm"
            variant="text"
            @click="updateSelected([])"
          >
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </div>

      <div class="grow" />

      <AssetStatusFilter
        v-model="ignoredFilter"
        :count="ignoredAssets.length"
        @refresh:ignored="fetchIgnoredAssets()"
      />

      <div class="w-full md:w-[25rem]">
        <TableFilter
          :matches="filters"
          :matchers="matchers"
          @update:matches="updateFilter($event)"
        />
      </div>
    </div>

    <CollectionHandler
      :collection="collection"
      @set-page="setPage($event)"
    >
      <template #default="{ data }">
        <RuiDataTable
          dense
          :value="selected"
          :rows="data"
          :loading="loading"
          :cols="cols"
          :expanded="expanded"
          :pagination.sync="paginationModel"
          :pagination-modifiers="{ external: true }"
          :sort.sync="sortModel"
          :sort-modifiers="{ external: true }"
          row-attr="identifier"
          data-cy="managed-assets-table"
          single-expand
          sticky-header
          outlined
          @input="updateSelected($event ?? [])"
        >
          <template #item.symbol="{ row }">
            <AssetDetailsBase
              :changeable="!loading"
              opens-details
              :asset="getAsset(row)"
            />
          </template>
          <template #item.address="{ row }">
            <HashLink
              v-if="row.address"
              :text="row.address"
              :chain="getChain(row.evmChain)"
              hide-alias-name
            />
          </template>
          <template #item.started="{ row }">
            <DateDisplay
              v-if="row.started"
              :timestamp="row.started"
            />
            <span v-else>-</span>
          </template>
          <template #item.type="{ row }">
            {{ formatType(row.assetType) }}
          </template>
          <template #item.ignored="{ row }">
            <div class="flex justify-start items-center gap-2">
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
                tooltip-class="max-w-[10rem]"
                :disabled="
                  !isAssetWhitelistedValue(row.identifier) && !isSpamAsset(row)
                "
              >
                <template #activator>
                  <RuiSwitch
                    color="primary"
                    hide-details
                    :disabled="
                      isAssetWhitelistedValue(row.identifier) || isSpamAsset(row)
                    "
                    :value="isAssetIgnored(row.identifier).value"
                    @input="toggleIgnoreAsset(row.identifier)"
                  />
                </template>
                {{
                  isSpamAsset(row)
                    ? t('ignore.spam.hint')
                    : t('ignore.whitelist.hint')
                }}
              </RuiTooltip>

              <ManagedAssetIgnoringMore
                v-if="row.assetType === EVM_TOKEN"
                :identifier="row.identifier"
                :is-spam="isSpamAsset(row)"
                @toggle-whitelist="toggleWhitelistAsset(row.identifier)"
                @toggle-spam="toggleSpam(row)"
              />
            </div>
          </template>
          <template #item.actions="{ row }">
            <RowActions
              v-if="row.assetType !== CUSTOM_ASSET"
              :edit-tooltip="t('asset_table.edit_tooltip')"
              :delete-tooltip="t('asset_table.delete_tooltip')"
              @edit-click="edit(row)"
              @delete-click="deleteAsset(row)"
            >
              <CopyButton
                :tooltip="t('asset_table.copy_identifier.tooltip')"
                :value="row.identifier"
              />
            </RowActions>
          </template>
          <template #expanded-item="{ row }">
            <AssetUnderlyingTokens
              v-if="row.underlyingTokens"
              :tokens="row.underlyingTokens"
            />
          </template>
          <template #item.expand="{ row }">
            <RuiTableRowExpander
              v-if="row.underlyingTokens && row.underlyingTokens.length > 0"
              :expanded="isExpanded(row.identifier)"
              @click="expand(row)"
            />
          </template>
        </RuiDataTable>
      </template>
    </CollectionHandler>
  </div>
</template>
