<script setup lang="ts">
import type { Nullable } from '@rotki/common';
import type { CustomAsset, CustomAssetRequestPayload } from '@/modules/assets/types';
import CustomAssetFormDialog from '@/modules/assets/admin/custom/CustomAssetFormDialog.vue';
import CustomAssetTable from '@/modules/assets/admin/custom/CustomAssetTable.vue';
import { useCustomAssetFields } from '@/modules/assets/admin/custom/use-custom-asset-fields';
import { type Filters, useCustomAssetFilter } from '@/modules/assets/admin/custom/use-custom-assets-filter';
import { useAssetManagementApi } from '@/modules/assets/api/use-asset-management-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useCommonTableProps } from '@/modules/core/table/use-common-table-props';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { identifier = null, mainPage = false } = defineProps<{
  identifier?: string | null;
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const types = ref<string[]>([]);

const router = useRouter();
const route = useRoute();

const { deleteCustomAsset, getCustomAssetTypes, queryAllCustomAssets } = useAssetManagementApi();
const { editableItem, expanded } = useCommonTableProps<CustomAsset>();
const openCustomAssetDialog = ref<boolean>(false);

const { showDeleteConfirmation } = useTableRowDeletion<CustomAsset>({
  confirm: item => ({
    message: t('asset_management.confirm_delete.message', { asset: item?.name ?? '' }),
    title: t('asset_management.confirm_delete.title'),
  }),
  deleteItem: item => deleteCustomAsset(item.identifier),
  errorMessage: (item, error) => t('asset_management.delete_error', {
    address: item.identifier,
    message: getErrorMessage(error),
  }),
  onDeleted: refresh,
});

const filterSchema = useCustomAssetFilter();
const fields = useCustomAssetFields(types);

const {
  collection,
  filter,
  isLoading: loading,
  pagination,
  refetch,
  sort,
} = useServerTable<
  CustomAsset,
  CustomAssetRequestPayload,
  Filters
>({
  fetch: queryAllCustomAssets,
  filterSchema,
  sort: {
    default: [{
      column: 'name',
      direction: 'desc',
    }],
  },
  urlState: routeWhen(mainPage),
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
    const asset = get(collection).data.find(({ identifier: id }) => id === assetId);
    if (asset)
      edit(asset);
  }
}

async function refreshTypes() {
  set(types, await getCustomAssetTypes());
}

async function refresh() {
  await Promise.all([refetch(), refreshTypes()]);
}

onMounted(async () => {
  await refresh();
  editAsset(identifier);

  const query = get(route).query;
  if (query.add) {
    add();
    await router.replace({ query: {} });
  }
});

watch(() => identifier, (assetId) => {
  editAsset(assetId);
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.custom_assets')]">
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        size="lg"
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
        size="lg"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('managed_asset_content.add_asset') }}
      </RuiButton>
    </template>
    <CustomAssetTable
      v-model:filters="filter"
      v-model:expanded="expanded"
      v-model:pagination="pagination"
      v-model:sort="sort"
      :assets="collection.data"
      :loading="loading"
      :server-item-length="collection.found"
      :fields="fields"
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
