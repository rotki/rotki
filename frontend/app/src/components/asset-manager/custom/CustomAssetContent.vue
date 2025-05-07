<script setup lang="ts">
import type { CustomAsset, CustomAssetRequestPayload } from '@/types/asset';
import type { Nullable } from '@rotki/common';
import CustomAssetFormDialog from '@/components/asset-manager/custom/CustomAssetFormDialog.vue';
import CustomAssetTable from '@/components/asset-manager/custom/CustomAssetTable.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { type Filters, type Matcher, useCustomAssetFilter } from '@/composables/filters/custom-assets';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useCommonTableProps } from '@/modules/table/use-common-table-props';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';

const props = withDefaults(
  defineProps<{
    identifier?: string | null;
    mainPage?: boolean;
  }>(),
  { identifier: null, mainPage: false },
);

const { t } = useI18n({ useScope: 'global' });

const { identifier, mainPage } = toRefs(props);

const types = ref<string[]>([]);

const router = useRouter();
const route = useRoute();

const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { deleteCustomAsset, getCustomAssetTypes, queryAllCustomAssets } = useAssetManagementApi();
const { editableItem, expanded } = useCommonTableProps<CustomAsset>();
const openCustomAssetDialog = ref<boolean>(false);

async function deleteAsset(assetId: string) {
  try {
    const success = await deleteCustomAsset(assetId);
    if (success)
      await refresh();
  }
  catch (error: any) {
    setMessage({
      description: t('asset_management.delete_error', {
        address: assetId,
        message: error.message,
      }),
    });
  }
}

const {
  fetchData,
  filters,
  isLoading: loading,
  matchers,
  pagination,
  sort,
  state,
} = usePaginationFilters<
  CustomAsset,
  CustomAssetRequestPayload,
  Filters,
  Matcher
>(queryAllCustomAssets, {
  defaultSortBy: [{
    column: 'name',
    direction: 'desc',
  }],
  filterSchema: () => useCustomAssetFilter(types),
  history: get(mainPage) ? 'router' : false,
});

function add() {
  set(editableItem, null);
  set(openCustomAssetDialog, true);
}

function edit(editAsset: CustomAsset) {
  set(editableItem, editAsset);
  set(openCustomAssetDialog, true);
}

function editAsset(assetId: Nullable<string>) {
  if (assetId) {
    const asset = get(state).data.find(({ identifier: id }) => id === assetId);
    if (asset)
      edit(asset);
  }
}

async function refreshTypes() {
  set(types, await getCustomAssetTypes());
}

async function refresh() {
  await Promise.all([fetchData(), refreshTypes()]);
}

function showDeleteConfirmation(item: CustomAsset) {
  show(
    {
      message: t('asset_management.confirm_delete.message', {
        asset: item?.name ?? '',
      }),
      title: t('asset_management.confirm_delete.title'),
    },
    async () => await deleteAsset(item.identifier),
  );
}

onMounted(async () => {
  await refresh();
  editAsset(get(identifier));

  const query = get(route).query;
  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
});

watch(identifier, (assetId) => {
  editAsset(assetId);
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.custom_assets')]">
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        :loading="loading"
        @click="refresh()"
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
    </template>
    <CustomAssetTable
      v-model:filters="filters"
      v-model:expanded="expanded"
      v-model:pagination="pagination"
      v-model:sort="sort"
      :assets="state.data"
      :loading="loading"
      :server-item-length="state.found"
      :matchers="matchers"
      @edit="edit($event)"
      @delete-asset="showDeleteConfirmation($event)"
    />
    <CustomAssetFormDialog
      v-model:open="openCustomAssetDialog"
      :types="types"
      :editable-item="editableItem"
      @refresh="refresh()"
    />
  </TablePageLayout>
</template>
