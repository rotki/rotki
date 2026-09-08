<script setup lang="ts">
import type { CexMapping, CexMappingRequestPayload } from '@/modules/assets/types';
import { omit } from 'es-toolkit';
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import ManageCexMappingTable from '@/modules/assets/admin/cex-mapping/ManageCexMappingTable.vue';
import { useCexMappingFields } from '@/modules/assets/admin/cex-mapping/use-cex-mapping-fields';
import { CexMappingFilterKeys, type Filters } from '@/modules/assets/admin/cex-mapping/use-cex-mapping-filter';
import { useMappingAdmin } from '@/modules/assets/admin/use-mapping-admin';
import { useAssetCexMappingApi } from '@/modules/assets/api/use-asset-cex-mapping-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });

const { deleteCexMapping, fetchAllCexMapping } = useAssetCexMappingApi();

const fields = useCexMappingFields();

const {
  collection,
  filter,
  isLoading: loading,
  pagination,
  refetch,
} = useServerTable<
  CexMapping,
  CexMappingRequestPayload,
  Filters
>({
  fetch: fetchAllCexMapping,
  fields,
  urlState: { mode: 'route' },
});

const { add, consumeAddQuery, edit, editMode, modelValue } = useMappingAdmin<CexMapping, Filters>({
  blank: () => ({ asset: '', location: '', locationSymbol: '' }),
  filter,
  seedFromFilter: {
    location: CexMappingFilterKeys.LOCATION,
    locationSymbol: CexMappingFilterKeys.LOCATION_SYMBOL,
  },
  seedFromQuery: { location: 'location', locationSymbol: 'locationSymbol' },
});

onMounted(async () => {
  await consumeAddQuery();
  await refetch();
});

const { showDeleteConfirmation } = useTableRowDeletion<CexMapping>({
  confirm: item => ({
    message: t('asset_management.cex_mapping.confirm_delete.message', {
      asset: item.locationSymbol,
      location: item.location || t('asset_management.cex_mapping.all_exchanges'),
    }),
    title: t('asset_management.cex_mapping.confirm_delete.title'),
  }),
  deleteItem: mapping => deleteCexMapping(omit(mapping, ['asset'])),
  errorMessage: (_item, error) => ({
    description: t('asset_management.cex_mapping.delete_error', {
      message: getErrorMessage(error),
    }),
  }),
  onDeleted: refetch,
});
</script>

<template>
  <TablePageLayout child>
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
        data-testid="managed-cex-mapping-add-btn"
        color="primary"
        size="lg"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('asset_management.cex_mapping.add_mapping') }}
      </RuiButton>
    </template>
    <RuiCard>
      <ManageCexMappingTable
        v-model:filters="filter"
        v-model:pagination="pagination"
        :collection="collection"
        :fields="fields"
        :loading="loading"
        @refresh="refetch()"
        @edit="edit($event)"
        @delete="showDeleteConfirmation($event)"
      />
      <ManageCexMappingFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        @refresh="refetch()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
