<script setup lang="ts">
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type {
  HistoricalPrice,
  HistoricalPriceFormPayload,
} from '@/types/prices';

const { t } = useI18n();

const sort: Ref<DataTableSortData> = ref([
  {
    column: 'timestamp',
    direction: 'desc' as const,
  },
]);

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('price_table.headers.from_asset'),
    key: 'fromAsset',
    sortable: true,
  },
  {
    label: '',
    key: 'wasWorth',
    cellClass: '!text-xs !text-rui-text-secondary',
  },
  {
    label: t('common.price'),
    key: 'price',
    align: 'end',
    sortable: true,
  },
  {
    label: t('price_table.headers.to_asset'),
    key: 'toAsset',
    sortable: true,
  },
  {
    label: '',
    key: 'on',
    cellClass: '!text-xs !text-rui-text-secondary',
  },
  {
    label: t('common.datetime'),
    key: 'timestamp',
    sortable: true,
  },
  {
    label: '',
    key: 'actions',
    class: 'w-[3rem]',
  },
]);

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '',
  timestamp: 0,
});

const price = ref<HistoricalPriceFormPayload>(emptyPrice());
const filter = ref<{ fromAsset?: string; toAsset?: string }>({});
const fromAsset = useRefPropVModel(filter, 'fromAsset');
const toAsset = useRefPropVModel(filter, 'toAsset');

const update = ref(false);

const router = useRouter();
const route = useRoute();

const { items, loading, save, deletePrice, refresh } = useHistoricPrices(
  filter,
  t,
);

const {
  openDialog,
  setOpenDialog,
  submitting,
  closeDialog,
  setSubmitFunc,
  trySubmit,
  setPostSubmitFunc,
} = useHistoricPriceForm();

function openForm(hPrice: HistoricalPrice | null = null) {
  set(update, !!hPrice);
  if (hPrice) {
    set(price, {
      ...hPrice,
      price: hPrice.price.toFixed() ?? '',
    });
  }
  else {
    set(price, {
      ...emptyPrice(),
      fromAsset: get(fromAsset) ?? '',
      toAsset: get(toAsset) ?? '',
    });
  }
  setOpenDialog(true);
}

const hideForm = function () {
  closeDialog();
  set(price, emptyPrice());
};

const { show } = useConfirmStore();

function showDeleteConfirmation(item: HistoricalPrice) {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message'),
    },
    () => deletePrice(item),
  );
}

onMounted(async () => {
  setSubmitFunc(() => save(get(price), get(update)));
  const query = get(route).query;

  if (query.add) {
    openForm();
    await router.replace({ query: {} });
  }
});

setPostSubmitFunc(() => refresh({ modified: true }));
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.manage_prices'),
      t('navigation_menu.manage_prices_sub.historic_prices'),
    ]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refresh()"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('price_table.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        @click="openForm()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('price_management.dialog.add_title') }}
      </RuiButton>
    </template>
    <RuiCard>
      <div class="flex flex-row flex-wrap mb-4 gap-2">
        <AssetSelect
          v-model="fromAsset"
          outlined
          :label="t('price_management.from_asset')"
          clearable
          class="flex-1"
          hide-details
        >
          <template #prepend>
            <RuiIcon name="filter-line" />
          </template>
        </AssetSelect>
        <AssetSelect
          v-model="toAsset"
          outlined
          class="flex-1"
          :label="t('price_management.to_asset')"
          clearable
          hide-details
        >
          <template #prepend>
            <RuiIcon name="filter-line" />
          </template>
        </AssetSelect>
      </div>
      <RuiDataTable
        outlined
        dense
        :cols="headers"
        :loading="loading"
        :rows="items"
        row-attr="fromAsset"
        :sort.sync="sort"
      >
        <template #item.fromAsset="{ row }">
          <AssetDetails :asset="row.fromAsset" />
        </template>
        <template #item.toAsset="{ row }">
          <AssetDetails :asset="row.toAsset" />
        </template>
        <template #item.timestamp="{ row }">
          <DateDisplay :timestamp="row.timestamp" />
        </template>
        <template #item.price="{ row }">
          <AmountDisplay :value="row.price" />
        </template>
        <template #item.wasWorth>
          {{ t('price_table.was_worth') }}
        </template>
        <template #item.on>
          {{ t('price_table.on') }}
        </template>
        <template #item.actions="{ row }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(row)"
            @edit-click="openForm(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <BigDialog
      :display="openDialog"
      :title="
        update
          ? t('price_management.dialog.edit_title')
          : t('price_management.dialog.add_title')
      "
      :loading="submitting"
      @confirm="trySubmit()"
      @cancel="hideForm()"
    >
      <HistoricPriceForm
        v-model="price"
        :edit="update"
      />
    </BigDialog>
  </TablePageLayout>
</template>
