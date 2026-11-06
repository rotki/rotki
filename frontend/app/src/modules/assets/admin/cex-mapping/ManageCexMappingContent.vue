<script setup lang="ts">
import type { CexMapping, CexMappingRequestPayload } from '@/modules/assets/types';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { omit } from 'es-toolkit';
import { CexMappingFilterKeys, type Filters } from '@/modules/assets/admin/cex-mapping/cex-mapping-filter-keys';
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import ManageCexMappingTable from '@/modules/assets/admin/cex-mapping/ManageCexMappingTable.vue';
import { useCexMappingFields } from '@/modules/assets/admin/cex-mapping/use-cex-mapping-fields';
import MappingAdminLayout from '@/modules/assets/admin/MappingAdminLayout.vue';
import { useMappingAdmin } from '@/modules/assets/admin/use-mapping-admin';
import { useAssetCexMappingApi } from '@/modules/assets/api/use-asset-cex-mapping-api';
import { fromRequest } from '@/modules/core/api/request-result';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

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
  fetch: async payload => fromRequest(async () => fetchAllCexMapping(payload)),
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

function deleteConfirm(item: CexMapping): RowDeleteQuestion {
  return {
    message: t('asset_management.cex_mapping.confirm_delete.message', {
      asset: item.locationSymbol,
      location: item.location || t('asset_management.cex_mapping.all_exchanges'),
    }),
    title: t('asset_management.cex_mapping.confirm_delete.title'),
  };
}

const { deleteRow, failure: deleteFailure } = useTableRowDeletion<CexMapping>({
  deleteItem: mapping => deleteCexMapping(omit(mapping, ['asset'])),
  failureTitle: () => t('asset_management.cex_mapping.delete_error'),
  onDeleted: refetch,
});
</script>

<template>
  <MappingAdminLayout
    :loading="loading"
    add-test-id="managed-cex-mapping-add-btn"
    :add-label="t('asset_management.cex_mapping.add_mapping')"
    @refresh="refetch()"
    @add="add()"
  >
    <FailureStrip
      v-if="deleteFailure"
      class="mb-4"
      :title="deleteFailure.title"
      :failure="deleteFailure.failure"
      data-testid="cex-mapping-delete-error"
    />
    <ManageCexMappingTable
      v-model:filters="filter"
      v-model:pagination="pagination"
      :collection="collection"
      :fields="fields"
      :loading="loading"
      :delete-confirm="deleteConfirm"
      @edit="edit($event)"
      @delete="deleteRow($event)"
    />
    <ManageCexMappingFormDialog
      v-model="modelValue"
      :edit-mode="editMode"
      @refresh="refetch()"
    />
  </MappingAdminLayout>
</template>
