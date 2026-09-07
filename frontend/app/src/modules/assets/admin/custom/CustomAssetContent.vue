<script setup lang="ts">
import CustomAssetFormDialog from '@/modules/assets/admin/custom/CustomAssetFormDialog.vue';
import CustomAssetTable from '@/modules/assets/admin/custom/CustomAssetTable.vue';
import { useCustomAssetDialog } from '@/modules/assets/admin/custom/use-custom-asset-dialog';
import { useCustomAssetsTable } from '@/modules/assets/admin/custom/use-custom-assets-table';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { identifier = null, mainPage = false } = defineProps<{
  identifier?: string | null;
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  collection,
  fields,
  loading,
  modelExpanded,
  modelFilter,
  pagination,
  refresh,
  showDeleteConfirmation,
  sort,
  types,
} = useCustomAssetsTable({
  mainPage: () => mainPage,
});

const {
  add,
  consumeAddQuery,
  edit,
  editAsset,
  modelEditableItem,
  modelOpenDialog,
} = useCustomAssetDialog({
  assets: () => get(collection).data,
  identifier: () => identifier,
});

onMounted(async () => {
  await refresh();
  editAsset(identifier);
  await consumeAddQuery();
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
        data-testid="managed-asset-add-btn"
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
      v-model:filters="modelFilter"
      v-model:expanded="modelExpanded"
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
      v-model:open="modelOpenDialog"
      :types="types"
      :editable-item="modelEditableItem"
      @refresh="refresh()"
    />
  </TablePageLayout>
</template>
