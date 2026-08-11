<script setup lang="ts">
import type { CexMapping, CexMappingRequestPayload } from '@/modules/assets/types';
import { omit } from 'es-toolkit';
import ManageCexMappingFormDialog from '@/modules/assets/admin/cex-mapping/ManageCexMappingFormDialog.vue';
import ManageCexMappingTable from '@/modules/assets/admin/cex-mapping/ManageCexMappingTable.vue';
import { useAssetCexMappingApi } from '@/modules/assets/api/use-asset-cex-mapping-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { firstQueryValue } from '@/modules/core/table/route';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { deleteCexMapping, fetchAllCexMapping } = useAssetCexMappingApi();

const selectedLocation = ref<string>('');
const selectedSymbol = ref<string>('');
const editMode = ref<boolean>(false);

const modelValue = ref<CexMapping>();

const extraParams = computed(() => {
  const location = get(selectedLocation);
  const symbol = get(selectedSymbol);
  const data: { location?: string; locationSymbol?: string } = {};
  if (location)
    data.location = location;
  if (symbol)
    data.locationSymbol = symbol;
  return data;
});

const {
  collection,
  isLoading: loading,
  pagination,
  refetch,
} = useServerTable<
  CexMapping,
  CexMappingRequestPayload
>({
  fetch: fetchAllCexMapping,
  params: [{
    fromQuery(query): void {
      set(selectedLocation, query.location || '');
      set(selectedSymbol, query.locationSymbol || '');
    },
    to: 'both',
    values: extraParams,
  }],
  urlState: { mode: 'route' },
});

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    await router.replace({ query: {} });
    add({
      location: firstQueryValue(query.location),
      locationSymbol: firstQueryValue(query.locationSymbol),
    });
  }

  await refetch();
});

function add(payload?: Partial<CexMapping>) {
  set(modelValue, {
    asset: '',
    location: get(selectedLocation) || '',
    locationSymbol: get(selectedSymbol) || '',
    ...payload,
  });
  set(editMode, false);
}

function edit(editMapping: CexMapping) {
  set(modelValue, editMapping);
  set(editMode, true);
}

const { showDeleteConfirmation } = useTableRowDeletion<CexMapping>({
  confirm: item => ({
    message: t('asset_management.cex_mapping.confirm_delete.message', {
      asset: item.locationSymbol,
      location: item.location || t('asset_management.cex_mapping.all_exchanges'),
    }),
    title: t('asset_management.cex_mapping.confirm_delete.title'),
  }),
  deleteItem: mapping => deleteCexMapping(omit(mapping, ['asset'])),
  errorMessage: (_item, error) => t('asset_management.cex_mapping.delete_error', {
    message: getErrorMessage(error),
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
        v-model:location="selectedLocation"
        v-model:symbol="selectedSymbol"
        v-model:pagination="pagination"
        :collection="collection"
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
