<script setup lang="ts">
import { useRefPropVModel } from '@/utils/model';
import { useConfirmStore } from '@/store/confirm';
import { useHistoricPriceForm } from '@/composables/price-manager/historic/form';
import { useHistoricPrices } from '@/composables/price-manager/historic';
import HistoricPriceForm from '@/components/price-manager/historic/HistoricPriceForm.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RowActions from '@/components/helper/RowActions.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import type { HistoricalPrice, HistoricalPriceFormPayload } from '@/types/prices';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';

const { t } = useI18n();

const sort = ref<DataTableSortData<HistoricalPrice>>([
  {
    column: 'timestamp',
    direction: 'desc' as const,
  },
]);

const headers = computed<DataTableColumn<HistoricalPrice>[]>(() => [
  {
    key: 'fromAsset',
    label: t('price_table.headers.from_asset'),
    sortable: true,
  },
  {
    cellClass: '!text-xs !text-rui-text-secondary',
    key: 'wasWorth',
    label: '',
  },
  {
    align: 'end',
    key: 'price',
    label: t('common.price'),
    sortable: true,
  },
  {
    key: 'toAsset',
    label: t('price_table.headers.to_asset'),
    sortable: true,
  },
  {
    cellClass: '!text-xs !text-rui-text-secondary',
    key: 'on',
    label: '',
  },
  {
    key: 'timestamp',
    label: t('common.datetime'),
    sortable: true,
  },
  {
    class: 'w-[3rem]',
    key: 'actions',
    label: '',
  },
]);

const emptyPrice: () => HistoricalPriceFormPayload = () => ({
  fromAsset: '',
  price: '',
  timestamp: 0,
  toAsset: '',
});

const price = ref<HistoricalPriceFormPayload>(emptyPrice());
const filter = ref<{ fromAsset?: string; toAsset?: string }>({});
const fromAsset = useRefPropVModel(filter, 'fromAsset');
const toAsset = useRefPropVModel(filter, 'toAsset');

const update = ref(false);

const router = useRouter();
const route = useRoute();

const { deletePrice, items, loading, refresh, save } = useHistoricPrices(filter, t);

const { closeDialog, openDialog, setOpenDialog, setPostSubmitFunc, setSubmitFunc, stateUpdated, submitting, trySubmit }
  = useHistoricPriceForm();

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
      message: t('price_table.delete.dialog.message'),
      title: t('price_table.delete.dialog.title'),
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
    :title="[t('navigation_menu.manage_prices'), t('navigation_menu.manage_prices_sub.historic_prices')]"
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
        />
        <AssetSelect
          v-model="toAsset"
          outlined
          class="flex-1"
          :label="t('price_management.to_asset')"
          clearable
          hide-details
        />
      </div>
      <RuiDataTable
        v-model:sort="sort"
        outlined
        dense
        :cols="headers"
        :loading="loading"
        :rows="items"
        row-attr="fromAsset"
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
      :title="update ? t('price_management.dialog.edit_title') : t('price_management.dialog.add_title')"
      :loading="submitting"
      :prompt-on-close="stateUpdated"
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
