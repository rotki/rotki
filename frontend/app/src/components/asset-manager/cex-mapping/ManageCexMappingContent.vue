<script setup lang="ts">
import type { CexMapping, CexMappingRequestPayload } from '@/types/asset';
import ManageCexMappingFormDialog from '@/components/asset-manager/cex-mapping/ManageCexMappingFormDialog.vue';
import ManageCexMappingTable from '@/components/asset-manager/cex-mapping/ManageCexMappingTable.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useAssetCexMappingApi } from '@/composables/api/assets/cex-mapping';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { omit } from 'es-toolkit';

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
  fetchData,
  isLoading: loading,
  pagination,
  state,
} = usePaginationFilters<
  CexMapping,
  CexMappingRequestPayload
>(fetchAllCexMapping, {
  extraParams,
  history: 'router',
  onUpdateFilters(query) {
    set(selectedLocation, query.location || '');
    set(selectedSymbol, query.locationSymbol || '');
  },
});

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    await router.replace({ query: {} });
    add({
      location: (query.location as string) || '',
      locationSymbol: (query.locationSymbol as string) || '',
    });
  }

  await fetchData();
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

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

async function confirmDelete(mapping: CexMapping) {
  try {
    const success = await deleteCexMapping(omit(mapping, ['asset']));
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
      message: t('asset_management.cex_mapping.confirm_delete.message', {
        asset: item.locationSymbol,
        location: item.location || t('asset_management.cex_mapping.all_exchanges'),
      }),
      title: t('asset_management.cex_mapping.confirm_delete.title'),
    },
    async () => await confirmDelete(item),
  );
}
</script>

<template>
  <TablePageLayout child>
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
        data-cy="managed-cex-mapping-add-btn"
        color="primary"
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
        :collection="state"
        :loading="loading"
        @refresh="fetchData()"
        @edit="edit($event)"
        @delete="showDeleteConfirmation($event)"
      />
      <ManageCexMappingFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        @refresh="fetchData()"
      />
    </RuiCard>
  </TablePageLayout>
</template>
