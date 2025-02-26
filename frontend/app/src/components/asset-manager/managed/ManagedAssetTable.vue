<script setup lang="ts">
import { some } from 'es-toolkit/compat';
import { CUSTOM_ASSET, EVM_TOKEN, IgnoredAssetHandlingType, type IgnoredAssetsHandlingType } from '@/types/asset';
import { uniqueStrings } from '@/utils/data';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { useMessageStore } from '@/store/message';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSpamAsset } from '@/composables/assets/spam';
import AssetUnderlyingTokens from '@/components/asset-manager/AssetUnderlyingTokens.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import ManagedAssetIgnoringMore from '@/components/asset-manager/managed/ManagedAssetIgnoringMore.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HashLink from '@/components/helper/HashLink.vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import AssetStatusFilter from '@/components/asset-manager/AssetStatusFilter.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import type { ActionStatus } from '@/types/action';
import type { SupportedAsset } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { Filters, Matcher } from '@/composables/filters/assets';
import type { Collection } from '@/types/collection';

interface IgnoredFilter {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}
const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const sortModel = defineModel<DataTableSortData<SupportedAsset>>('sort', { required: true });

const selected = defineModel<string[]>('selected', { required: true });

const filtersModel = defineModel<Filters>('filters', { required: true });

const ignoredFilter = defineModel<IgnoredFilter>('ignoredFilter', { required: true });

const props = withDefaults(
  defineProps<{
    collection: Collection<SupportedAsset>;
    matchers: Matcher[];
    expanded: SupportedAsset[];
    ignoredAssets: string[];
    loading?: boolean;
  }>(),
  { loading: false },
);

const emit = defineEmits<{
  (e: 'refresh'): void;
  (e: 'edit', asset: SupportedAsset): void;
  (e: 'delete-asset', asset: SupportedAsset): void;
  (e: 'update:expanded', expandedAssets: SupportedAsset[]): void;
}>();

const { collection } = toRefs(props);

const { t } = useI18n();

const cols = computed<DataTableColumn<SupportedAsset>[]>(() => [
  {
    cellClass: 'py-0',
    class: 'w-full',
    key: 'symbol',
    label: t('common.asset'),
    sortable: true,
  },
  {
    cellClass: '!text-nowrap py-0',
    key: 'type',
    label: t('common.type'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'min-w-[11.375rem]',
    key: 'address',
    label: t('common.address'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    class: 'min-w-[10rem]',
    key: 'started',
    label: t('asset_table.headers.started'),
    sortable: true,
  },
  {
    cellClass: 'py-0',
    key: 'ignored',
    label: t('assets.ignore'),
  },
  {
    key: 'actions',
    label: '',
  },
]);

const edit = (asset: SupportedAsset) => emit('edit', asset);
const deleteAsset = (asset: SupportedAsset) => emit('delete-asset', asset);

function updateExpanded(expandedAssets: SupportedAsset[]) {
  return emit('update:expanded', expandedAssets);
}

const disabledIgnoreActions = computed(() => {
  const { ignoredAssetsHandling } = get(ignoredFilter);
  return {
    ignore: ignoredAssetsHandling === IgnoredAssetHandlingType.SHOW_ONLY,
    unIgnore: ignoredAssetsHandling === IgnoredAssetHandlingType.EXCLUDE,
  };
});

const formatType = (string?: string | null) => toSentenceCase(string ?? 'EVM token');

function getAsset(item: SupportedAsset) {
  const name
    = item.name
      ?? item.symbol
      ?? (isEvmIdentifier(item.identifier) ? getAddressFromEvmIdentifier(item.identifier) : item.identifier);

  return {
    customAssetType: item.customAssetType ?? '',
    identifier: item.identifier,
    isCustomAsset: item.assetType === CUSTOM_ASSET,
    name,
    symbol: item.symbol ?? '',
  };
}

const { setMessage } = useMessageStore();
const { fetchIgnoredAssets, ignoreAsset, ignoreAssetWithConfirmation, isAssetIgnored, unignoreAsset } = useIgnoredAssetsStore();
const { isAssetWhitelisted, unWhitelistAsset, whitelistAsset } = useWhitelistedAssetsStore();

const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();

const { getChain } = useSupportedChains();

async function toggleIgnoreAsset(asset: SupportedAsset) {
  const { identifier, name, symbol } = asset;
  if (get(isAssetIgnored(identifier))) {
    await unignoreAsset(identifier);
  }
  else {
    await ignoreAssetWithConfirmation(identifier, symbol || name);
  }

  if (get(ignoredFilter).ignoredAssetsHandling !== 'none')
    emit('refresh');
}

const isSpamAsset = (asset: SupportedAsset) => asset.protocol === 'spam';

const { refetchAssetInfo } = useAssetInfoRetrieval();

async function toggleSpam(item: SupportedAsset) {
  const { identifier } = item;
  if (isSpamAsset(item))
    await removeAssetFromSpamList(identifier);
  else
    await markAssetsAsSpam([identifier]);

  refetchAssetInfo(identifier);

  emit('refresh');
}

async function toggleWhitelistAsset(identifier: string) {
  if (get(isAssetWhitelisted(identifier)))
    await unWhitelistAsset(identifier);
  else await whitelistAsset(identifier);

  emit('refresh');
}

async function massIgnore(ignored: boolean) {
  const ids = get(selected)
    .filter((identifier) => {
      const isItemIgnored = get(isAssetIgnored(identifier));
      return ignored ? !isItemIgnored : isItemIgnored;
    })
    .filter(uniqueStrings);

  let status: ActionStatus;

  if (ids.length === 0) {
    const choice = ignored ? 1 : 2;
    setMessage({
      description: t('ignore.no_items.description', choice),
      success: false,
      title: t('ignore.no_items.title', choice),
    });
    return;
  }

  if (ignored)
    status = await ignoreAsset(ids);
  else status = await unignoreAsset(ids);

  if (status.success) {
    set(selected, []);
    if (get(ignoredFilter).ignoredAssetsHandling !== 'none')
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

const disabledRows = computed(() => {
  const data = get(collection).data;

  return data.filter(item => get(isAssetWhitelisted(item.identifier)) || isSpamAsset(item));
});
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
            @click="selected = []"
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
          v-model:matches="filtersModel"
          :matchers="matchers"
        />
      </div>
    </div>

    <CollectionHandler
      :collection="collection"
      @set-page="setPage($event)"
    >
      <template #default="{ data }">
        <RuiDataTable
          v-model="selected"
          v-model:pagination.external="paginationModel"
          v-model:sort.external="sortModel"
          dense
          :value="selected"
          :rows="data"
          :loading="loading"
          :cols="cols"
          :expanded="expanded"
          :disabled-rows="disabledRows"
          row-attr="identifier"
          data-cy="managed-assets-table"
          single-expand
          sticky-header
          outlined
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
              :chain="row?.evmChain ? getChain(row.evmChain) : undefined"
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
            <div
              v-if="row.assetType !== CUSTOM_ASSET"
              class="flex justify-start items-center gap-2"
            >
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
                tooltip-class="max-w-[10rem]"
                :disabled="!isSpamAsset(row)"
              >
                <template #activator>
                  <RuiSwitch
                    color="primary"
                    hide-details
                    :disabled="isSpamAsset(row)"
                    :model-value="isAssetIgnored(row.identifier).value"
                    @update:model-value="toggleIgnoreAsset(row)"
                  />
                </template>
                {{ t('ignore.spam.hint') }}
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
