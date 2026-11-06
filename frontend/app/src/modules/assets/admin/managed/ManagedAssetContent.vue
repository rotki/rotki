<script setup lang="ts">
import ManagedAssetFormDialog from '@/modules/assets/admin/managed/ManagedAssetFormDialog.vue';
import ManagedAssetTable from '@/modules/assets/admin/managed/ManagedAssetTable.vue';
import { useManagedAssetForm } from '@/modules/assets/admin/managed/use-managed-asset-form';
import { useManagedAssetsTable } from '@/modules/assets/admin/managed/use-managed-assets-table';
import MergeDialog from '@/modules/assets/admin/MergeDialog.vue';
import RestoreAssetDbButton from '@/modules/assets/admin/RestoreAssetDbButton.vue';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { identifier = null, mainPage = false } = defineProps<{
  identifier?: string | null;
  mainPage?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const mergeTool = ref<boolean>(false);
const openAction = ref<boolean>(false);

const router = useRouter();

const {
  add,
  assetTypes,
  assetTypesFailure,
  edit,
  editAsset,
  editMode,
  loadAssetTypes,
  modelValue,
} = useManagedAssetForm(() => identifier);

const {
  assets,
  deleteAsset,
  deleteConfirm,
  deleteFailure,
  fields,
  loading,
  modelExpanded,
  modelFilter,
  modelIgnoredAssetsHandling,
  modelPillParams,
  modelSelectedRows,
  pagination,
  refetch,
  sort,
} = useManagedAssetsTable(() => mainPage, assetTypes);

const { consumeAddQuery } = useAddQuery(add);

onMounted(async () => {
  await refetch();

  if (identifier) {
    await editAsset(identifier);
    await router.replace({ query: {} });
    return;
  }

  await consumeAddQuery();
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.manage_assets'), t('navigation_menu.manage_assets_sub.assets')]">
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
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
            class="text-rui-text-secondary!"
            :aria-label="t('common.actions.more')"
            v-bind="attrs"
          >
            <RuiIcon name="lu-ellipsis-vertical" />
          </RuiButton>
        </template>
        <RestoreAssetDbButton
          dropdown
          @close="openAction = false"
        />
        <RuiTooltip
          :open-delay="400"
          class="w-full"
          :options="{ placement: 'left' }"
          :class-names="{ tooltip: 'max-w-50' }"
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

    <FailureStrip
      v-if="assetTypesFailure"
      class="mb-4"
      :title="t('asset_form.types.load_failed')"
      :failure="assetTypesFailure"
      data-testid="managed-asset-types-error"
      @retry="loadAssetTypes()"
    />
    <FailureStrip
      v-if="deleteFailure"
      class="mb-4"
      :retryable="false"
      :title="deleteFailure.title"
      :failure="deleteFailure.error"
      data-testid="managed-asset-delete-error"
    />
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
      :fields="fields"
      :delete-confirm="deleteConfirm"
      @refresh="refetch()"
      @edit="edit($event)"
      @delete-asset="deleteAsset($event)"
    />

    <MergeDialog v-model="mergeTool" />

    <ManagedAssetFormDialog
      v-model="modelValue"
      :asset-types="assetTypes"
      :edit-mode="editMode"
      @refresh="refetch()"
    />
  </TablePageLayout>
</template>
