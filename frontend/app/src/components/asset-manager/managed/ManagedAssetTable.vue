<script setup lang="ts">
import {
  CUSTOM_ASSET,
  EVM_TOKEN,
  type IgnoredAssetsHandlingType,
} from '@/types/asset';
import type { Filters, Matcher } from '@/composables/filters/assets';
import type {
  DataTableColumn,
  DataTableOptions,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { Ref } from 'vue';
import type { TablePagination } from '@/types/pagination';
import type { SupportedAsset } from '@rotki/common/lib/data';
import type { ActionStatus } from '@/types/action';

const props = withDefaults(
  defineProps<{
    tokens: SupportedAsset[];
    serverItemLength: number;
    matchers: Matcher[];
    filters: Filters;
    expanded: SupportedAsset[];
    selected: string[];
    options: TablePagination<SupportedAsset>;
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
  (e: 'update:options', options: DataTableOptions): void;
  (e: 'update:filters', filters: Filters): void;
  (e: 'update:selected', selectedAssets: string[]): void;
  (e: 'update:expanded', expandedAssets: SupportedAsset[]): void;
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

const sort: Ref<DataTableSortData> = ref({
  column: 'symbol',
  direction: 'asc' as const,
});

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('common.asset'),
    key: 'symbol',
    sortable: true,
    cellClass: 'py-0',
  },
  {
    label: t('common.type'),
    key: 'type',
    sortable: true,
    cellClass: 'py-0',
  },
  {
    label: t('common.address'),
    key: 'address',
    sortable: true,
    cellClass: 'py-0',
  },
  {
    label: t('asset_table.headers.started'),
    key: 'started',
    sortable: true,
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
    sortable: false,
  },
]);
const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

function updatePagination(options: DataTableOptions) {
  return emit('update:options', options);
}
const updateFilter = (filters: Filters) => emit('update:filters', filters);

function updateSelected(selectedAssets: string[]) {
  emit('update:selected', selectedAssets);
}

function updateExpanded(expandedAssets: SupportedAsset[]) {
  return emit('update:expanded', expandedAssets);
}

const ignoredFilter = useKebabVModel(props, 'ignoredFilter', emit);

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
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();
const { isAssetWhitelisted, whitelistAsset, unWhitelistAsset }
  = useWhitelistedAssetsStore();

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
</script>

<template>
  <div data-cy="managed-assets-table">
    <div class="flex flex-row flex-wrap items-center gap-2 mb-4">
      <div class="flex flex-row gap-2">
        <IgnoreButtons
          :disabled="selected.length === 0"
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
      />

      <div class="w-full md:w-[25rem]">
        <TableFilter
          :matches="filters"
          :matchers="matchers"
          @update:matches="updateFilter($event)"
        />
      </div>
    </div>

    <RuiDataTable
      :value="selected"
      :rows="tokens"
      :loading="loading"
      :cols="tableHeaders"
      :expanded="expanded"
      :pagination="{
        limit: options.itemsPerPage,
        page: options.page,
        total: serverItemLength,
      }"
      :pagination-modifiers="{ external: true }"
      :sort.sync="sort"
      :sort-modifiers="{ external: true }"
      :sticky-offset="64"
      row-attr="identifier"
      data-cy="managed-assets-table"
      single-expand
      sticky-header
      outlined
      @update:options="updatePagination($event)"
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
        <div class="flex justify-start">
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
            tooltip-class="max-w-[10rem]"
            :disabled="
              !isAssetWhitelistedValue(row.identifier) && !isSpamAsset(row)
            "
          >
            <template #activator>
              <VSwitch
                :disabled="
                  isAssetWhitelistedValue(row.identifier) || isSpamAsset(row)
                "
                :input-value="isAssetIgnored(row.identifier)"
                @change="toggleIgnoreAsset(row.identifier)"
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
          :asset="row"
        />
      </template>
      <template #item.expand="{ row }">
        <RuiTableRowExpander
          v-if="row.underlyingTokens && row.underlyingTokens.length > 0"
          :expanded="expanded.includes(row)"
          @click="updateExpanded(expanded.includes(row) ? [] : [row])"
        />
      </template>
    </RuiDataTable>
  </div>
</template>
