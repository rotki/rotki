<script setup lang="ts">
import type { Nullable, SupportedAsset } from '@rotki/common';
import { isEqual, keyBy } from 'es-toolkit';
import ManagedAssetFormDialog from '@/components/asset-manager/managed/ManagedAssetFormDialog.vue';
import ManagedAssetTable from '@/components/asset-manager/managed/ManagedAssetTable.vue';
import MergeDialog from '@/components/asset-manager/MergeDialog.vue';
import RestoreAssetDbButton from '@/components/asset-manager/RestoreAssetDbButton.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { type Filters, type Matcher, useAssetFilter } from '@/composables/filters/assets';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useCommonTableProps } from '@/modules/table/use-common-table-props';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { type AssetRequestPayload, EVM_TOKEN, type IgnoredAssetsHandlingType } from '@/types/asset';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false },
);

const { t } = useI18n({ useScope: 'global' });

const { identifier, mainPage } = toRefs(props);

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
const { ignoredAssets } = storeToRefs(useIgnoredAssetsStore());
const { getAssetTypes } = useAssetManagementApi();

const { deleteCacheKey } = useAssetCacheStore();

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
  history: get(mainPage) ? 'router' : false,
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
  catch (error: any) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: identifier,
        message: error.message,
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
  const idToEdit = get(identifier);
  const query = get(route).query;

  if (idToEdit || query.add) {
    if (idToEdit)
      await editAsset(get(identifier));
    else add();

    await router.replace({ query: {} });
  }
});

watch(identifier, async (assetId) => {
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
  catch (error: any) {
    setMessage({
      description: t('asset_form.types.error', {
        message: error.message,
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
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('managed_asset_content.add_asset') }}
      </RuiButton>
      <RuiMenu :popper="{ placement: 'bottom-end' }">
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="!p-2"
            v-bind="attrs"
          >
            <RuiIcon name="lu-ellipsis-vertical" />
          </RuiButton>
        </template>
        <div class="py-2">
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
                @click="mergeTool = true"
              >
                <template #prepend>
                  <RuiIcon name="lu-combine" />
                </template>
                {{ t('asset_management.merge_assets') }}
              </RuiButton>
            </template>
            {{ t('asset_management.merge_assets_tooltip') }}
          </RuiTooltip>
        </div>
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
