<script setup lang="ts">
import { omit } from 'lodash-es';
import type { CexMapping, CexMappingRequestPayload } from '@/types/asset';
import type { Collection } from '@/types/collection';

const { t } = useI18n();

const { fetchAllCexMapping, deleteCexMapping } = useAssetCexMappingApi();

const selectedLocation: Ref<string> = ref('');
const selectedSymbol: Ref<string> = ref('');

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
  state,
  isLoading: loading,
  editableItem,
  fetchData,
  pagination,
} = usePaginationFilters<
  CexMapping,
  CexMappingRequestPayload,
  CexMapping,
  Collection<CexMapping>
>(null, true, useEmptyFilter, fetchAllCexMapping, {
  onUpdateFilters(query) {
    set(selectedLocation, query.location || '');
    set(selectedSymbol, query.locationSymbol || '');
  },
  extraParams,
});

onMounted(async () => {
  await fetchData();
});

const { setOpenDialog, setPostSubmitFunc } = useCexMappingForm();
setPostSubmitFunc(fetchData);

function add() {
  set(editableItem, null);
  setOpenDialog(true);
}

function edit(editMapping: CexMapping) {
  set(editableItem, editMapping);
  setOpenDialog(true);
}

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

async function confirmDelete(mapping: CexMapping) {
  try {
    const success = await deleteCexMapping(omit(mapping, 'asset'));
    if (success)
      await fetchData();
  }
  catch (error: any) {
    setMessage({
      description: t('asset_management.cex_mapping.delete_error', {
        message: error.message,
      }),
    });
  }
}

function showDeleteConfirmation(item: CexMapping) {
  show(
    {
      title: t('asset_management.cex_mapping.confirm_delete.title'),
      message: t('asset_management.cex_mapping.confirm_delete.message', {
        asset: item.locationSymbol,
        location: item.location || t('asset_management.cex_mapping.all_exchanges'),
      }),
    },
    async () => await confirmDelete(item),
  );
}

const dialogTitle = computed<string>(() =>
  get(editableItem)
    ? t('asset_management.cex_mapping.edit_title')
    : t('asset_management.cex_mapping.add_title'),
);
</script>

<template>
  <TablePageLayout
    child
    class="md:-mt-[4.5rem]"
  >
    <template #buttons>
      <RuiButton
        color="primary"
        variant="outlined"
        :loading="loading"
        @click="fetchData()"
      >
        <template #prepend>
          <RuiIcon name="refresh-line" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>

      <RuiButton
        data-cy="managed-cex-mapping-add-btn"
        color="primary"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('asset_management.cex_mapping.add_mapping') }}
      </RuiButton>
    </template>
    <RuiCard>
      <ManageCexMappingTable
        :collection="state"
        :location.sync="selectedLocation"
        :symbol.sync="selectedSymbol"
        :loading="loading"
        :pagination.sync="pagination"
        @refresh="fetchData()"
        @edit="edit($event)"
        @delete="showDeleteConfirmation($event)"
      />
      <ManageCexMappingFormDialog
        :title="dialogTitle"
        :editable-item="editableItem"
        :selected-location="selectedLocation"
      />
    </RuiCard>
  </TablePageLayout>
</template>
