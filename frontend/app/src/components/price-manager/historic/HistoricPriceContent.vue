<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import {
  type HistoricalPrice,
  type HistoricalPriceFormPayload
} from '@/types/prices';
import { type Nullable } from '@/types';

const { t } = useI18n();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'wasWorth',
    sortable: false
  },
  {
    text: t('common.price'),
    value: 'price',
    align: 'end'
  },
  {
    text: t('price_table.headers.to_asset'),
    value: 'toAsset'
  },
  {
    text: '',
    value: 'on',
    sortable: false
  },
  {
    text: t('common.datetime'),
    value: 'timestamp'
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  }
]);

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0',
  timestamp: 0
});

const price = ref<HistoricalPriceFormPayload>(emptyPrice());
const filter = reactive<{
  fromAsset: Nullable<string>;
  toAsset: Nullable<string>;
}>({
  fromAsset: null,
  toAsset: null
});
const update = ref(false);

const router = useRouter();
const route = useRoute();

const { items, loading, save, deletePrice, refresh } = useHistoricPrices(
  filter,
  t
);

const {
  openDialog,
  setOpenDialog,
  submitting,
  closeDialog,
  setSubmitFunc,
  trySubmit,
  setPostSubmitFunc
} = useHistoricPriceForm();

const openForm = (hPrice: HistoricalPrice | null = null) => {
  set(update, !!hPrice);
  if (hPrice) {
    set(price, {
      ...hPrice,
      price: hPrice.price.toFixed() ?? ''
    });
  } else {
    set(price, {
      ...emptyPrice(),
      fromAsset: filter.fromAsset ?? '',
      toAsset: filter.toAsset ?? ''
    });
  }
  setOpenDialog(true);
};

const hideForm = function () {
  closeDialog();
  set(price, emptyPrice());
};

const { show } = useConfirmStore();

const showDeleteConfirmation = (item: HistoricalPrice) => {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message')
    },
    () => deletePrice(item)
  );
};

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
      t('navigation_menu.manage_prices_sub.historic_prices')
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
      <RuiButton color="primary" @click="openForm()">
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('price_management.dialog.add_title') }}
      </RuiButton>
    </template>
    <RuiCard>
      <div class="flex flex-row flex-wrap mb-4 gap-2">
        <AssetSelect
          v-model="filter.fromAsset"
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
          v-model="filter.toAsset"
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
      <DataTable
        :items="items"
        :headers="headers"
        :loading="loading"
        sort-by="timestamp"
      >
        <template #item.fromAsset="{ item }">
          <AssetDetails :asset="item.fromAsset" />
        </template>
        <template #item.toAsset="{ item }">
          <AssetDetails :asset="item.toAsset" />
        </template>
        <template #item.timestamp="{ item }">
          <DateDisplay :timestamp="item.timestamp" />
        </template>
        <template #item.price="{ item }">
          <AmountDisplay :value="item.price" />
        </template>
        <template #item.wasWorth>{{ t('price_table.was_worth') }}</template>
        <template #item.on>{{ t('price_table.on') }}</template>
        <template #item.actions="{ item }">
          <RowActions
            :disabled="loading"
            :delete-tooltip="t('price_table.actions.delete.tooltip')"
            :edit-tooltip="t('price_table.actions.edit.tooltip')"
            @delete-click="showDeleteConfirmation(item)"
            @edit-click="openForm(item)"
          />
        </template>
      </DataTable>
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
      <HistoricPriceForm v-model="price" :edit="update" />
    </BigDialog>
  </TablePageLayout>
</template>
