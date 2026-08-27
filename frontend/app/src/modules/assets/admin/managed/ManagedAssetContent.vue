<script setup lang="ts">
import ManagedAssetFormDialog from '@/modules/assets/admin/managed/ManagedAssetFormDialog.vue';
import ManagedAssetTable from '@/modules/assets/admin/managed/ManagedAssetTable.vue';
import { useManagedAssetForm } from '@/modules/assets/admin/managed/use-managed-asset-form';
import { useManagedAssetsTable } from '@/modules/assets/admin/managed/use-managed-assets-table';
import MergeDialog from '@/modules/assets/admin/MergeDialog.vue';
import RestoreAssetDbButton from '@/modules/assets/admin/RestoreAssetDbButton.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { identifier = null, mainPage = false } = defineProps<{
  identifier?: string | null;
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const mergeTool = ref<boolean>(false);
const openAction = ref<boolean>(false);

const router = useRouter();
const route = useRoute();

const { add, assetTypes, edit, editAsset, editMode, modelValue } = useManagedAssetForm(() => identifier);

const {
  assets,
  fields,
  loading,
  modelExpanded,
  modelFilter,
  modelIgnoredAssetsHandling,
  modelPillParams,
  modelSelectedRows,
  pagination,
  refetch,
  setPage,
  showDeleteConfirmation,
  sort,
} = useManagedAssetsTable(() => mainPage, assetTypes);

onMounted(async () => {
  await refetch();
  const query = get(route).query;

  if (identifier || query.add) {
    if (identifier)
      await editAsset(identifier);
    else add();

    await router.replace({ query: {} });
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
        @click="refetch()"
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
      <RuiMenu
        v-model="openAction"
        :options="{ placement: 'bottom-end' }"
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
          :options="{ placement: 'left' }"
          :class-names="{ tooltip: 'max-w-[200px]' }"
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
        v-model:filters="modelFilter"
        v-model:pill-params="modelPillParams"
        v-model:expanded="modelExpanded"
        v-model:selected="modelSelectedRows"
        v-model:pagination="pagination"
        v-model:sort="sort"
        :ignored-handling="modelIgnoredAssetsHandling"
        :collection="assets"
        :loading="loading"
        :change="!loading"
        :fields="fields"
        @refresh="refetch()"
        @edit="edit($event)"
        @delete-asset="showDeleteConfirmation($event)"
        @update:page="setPage($event)"
      />

      <ManagedAssetFormDialog
        v-model="modelValue"
        :asset-types="assetTypes"
        :edit-mode="editMode"
        @refresh="refetch()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
