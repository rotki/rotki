<script setup lang="ts">
import type { Nullable, SupportedAsset } from '@rotki/common';
import { isEqual, keyBy } from 'es-toolkit';
import ManagedAssetFormDialog from '@/modules/assets/admin/managed/ManagedAssetFormDialog.vue';
import ManagedAssetTable from '@/modules/assets/admin/managed/ManagedAssetTable.vue';
import MergeDialog from '@/modules/assets/admin/MergeDialog.vue';
import RestoreAssetDbButton from '@/modules/assets/admin/RestoreAssetDbButton.vue';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { type AssetRequestPayload, EVM_TOKEN, type IgnoredAssetsHandlingType } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { type Filters, type Matcher, useAssetFilter } from '@/modules/core/table/filters/use-assets-filter';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { identifier = null, mainPage = false } = defineProps<{
  identifier?: string | null;
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const mergeTool = ref<boolean>(false);
const ignoredFilter = ref<{
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>({
  ignoredAssetsHandling: 'exclude',
  onlyShowOwned: false,
  onlyShowWhitelisted: false,
});

const modelValue = ref<SupportedAsset>();
const editMode = ref<boolean>(false);
const assetTypes = ref<string[]>([]);
const openAction = ref<boolean>(false);

const { expanded, selected } = useCommonTableProps<SupportedAsset>();

const extraParams = computed(() => {
  const { ignoredAssetsHandling, onlyShowOwned, onlyShowWhitelisted } = get(ignoredFilter);
  return {
    ignoredAssetsHandling,
    showUserOwnedAssetsOnly: onlyShowOwned.toString(),
    showWhitelistedAssetsOnly: onlyShowWhitelisted.toString(),
  };
});

const router = useRouter();
const route = useRoute();
const { deleteAsset, queryAllAssets } = useAssetManagementApi();
const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { ignoredAssets } = storeToRefs(useAssetsStore());
const { getAssetTypes } = useAssetManagementApi();

const { deleteCacheKey } = useAssetInfoCache();

async function confirmDelete(toDeleteAsset: SupportedAsset) {
  await deleteAssetHandler(toDeleteAsset.identifier);
}

const {
  fetchData,
  filters,
  isLoading: loading,
  matchers,
  pagination,
  setPage,
  sort,
  state: assets,
} = usePaginationFilters<
  SupportedAsset,
  AssetRequestPayload,
  Filters,
  Matcher
>(queryAllAssets, {
  defaultSortBy: {
    column: 'symbol',
    direction: 'asc',
  },
  extraParams,
  filterSchema: () => useAssetFilter(assetTypes),
  history: mainPage ? 'router' : false,
  onUpdateFilters(query) {
    set(ignoredFilter, {
      ignoredAssetsHandling: query.ignoredAssetsHandling || 'exclude',
      onlyShowOwned: query.showUserOwnedAssetsOnly === 'true',
      onlyShowWhitelisted: query.showWhitelistedAssetsOnly === 'true',
    });
  },
});

function add() {
  set(modelValue, {
    active: true,
    address: '',
    assetType: EVM_TOKEN,
    customAssetType: '',
    decimals: null,
    ended: null,
    forked: null,
    identifier: '',
    protocol: '',
    underlyingTokens: null,
  });
  set(editMode, false);
}

function edit(editAsset: SupportedAsset) {
  set(modelValue, editAsset);
  set(editMode, true);
}

async function editAsset(assetId: Nullable<string>) {
  if (assetId) {
    const all = await queryAllAssets({
      identifiers: [assetId],
      limit: 1,
      offset: 0,
    });

    const foundAsset = all.data[0];
    if (foundAsset)
      edit(foundAsset);
  }
}

async function deleteAssetHandler(identifier: string) {
  try {
    const success = await deleteAsset(identifier);
    if (success) {
      await fetchData();
      deleteCacheKey(identifier);
    }
  }
  catch (error: unknown) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: identifier,
        message: getErrorMessage(error),
      }),
    });
  }
}

const assetsMap = computed(() => keyBy(get(assets).data, item => item.identifier));

const selectedRows = computed({
  get() {
    return get(selected).map(({ identifier }) => identifier);
  },
  set(identifiers: string[]) {
    set(
      selected,
      identifiers.map(identifier => get(assetsMap)[identifier]),
    );
  },
});

function showDeleteConfirmation(item: SupportedAsset) {
  show(
    {
      message: t('asset_management.confirm_delete.message', {
        asset: item?.symbol ?? '',
      }),
      title: t('asset_management.confirm_delete.title'),
    },
    async () => await confirmDelete(item),
  );
}

onMounted(async () => {
  await fetchData();
  const query = get(route).query;

  if (identifier || query.add) {
    if (identifier)
      await editAsset(identifier);
    else add();

    await router.replace({ query: {} });
  }
});

watch(() => identifier, async (assetId) => {
  await editAsset(assetId);
});

watch(ignoredFilter, (oldValue, newValue) => {
  if (!isEqual(oldValue, newValue))
    setPage(1);
});

onBeforeMount(async () => {
  try {
    set(assetTypes, await getAssetTypes());
  }
  catch (error: unknown) {
    setMessage({
      description: t('asset_form.types.error', {
        message: getErrorMessage(error),
      }),
    });
  }
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.assets')]">
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        size="lg"
        :loading="loading"
        @click="fetchData()"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton
        data-cy="managed-asset-add-btn"
        color="primary"
        size="lg"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('managed_asset_content.add_asset') }}
      </RuiButton>
      <RuiMenu
        v-model="openAction"
        :popper="{ placement: 'bottom-end' }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="lg"
            v-bind="attrs"
          >
            <RuiIcon name="lu-ellipsis-vertical" />
          </RuiButton>
        </template>
        <RestoreAssetDbButton dropdown />
        <RuiTooltip
          :open-delay="400"
          class="w-full"
          :popper="{ placement: 'left' }"
          tooltip-class="max-w-[200px]"
        >
          <template #activator>
            <RuiButton
              variant="list"
              @click="mergeTool = true; openAction = false"
            >
              <template #prepend>
                <RuiIcon name="lu-combine" />
              </template>
              {{ t('asset_management.merge_assets') }}
            </RuiButton>
          </template>
          {{ t('asset_management.merge_assets_tooltip') }}
        </RuiTooltip>
      </RuiMenu>
    </template>

    <RuiCard>
      <MergeDialog v-model="mergeTool" />

      <ManagedAssetTable
        v-model:filters="filters"
        v-model:ignored-filter="ignoredFilter"
        v-model:expanded="expanded"
        v-model:selected="selectedRows"
        v-model:pagination="pagination"
        v-model:sort="sort"
        :collection="assets"
        :loading="loading"
        :change="!loading"
        :matchers="matchers"
        :ignored-assets="ignoredAssets"
        @refresh="fetchData()"
        @edit="edit($event)"
        @delete-asset="showDeleteConfirmation($event)"
        @update:page="setPage($event)"
      />

      <ManagedAssetFormDialog
        v-model="modelValue"
        :asset-types="assetTypes"
        :edit-mode="editMode"
        @refresh="fetchData()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
