<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { isNft } from '@/utils/nft';
import { type ManualPrice, type ManualPriceFormPayload } from '@/types/prices';
import { type Nullable } from '@/types';
import { useLatestPrices } from '@/composables/price-manager/latest';

const { t } = useI18n();

const emptyPrice: () => ManualPriceFormPayload = () => ({
  fromAsset: '',
  toAsset: '',
  price: '0'
});

const price = ref<ManualPriceFormPayload>(emptyPrice());
const filter = ref<Nullable<string>>(null);
const update = ref(false);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('price_table.headers.from_asset'),
    value: 'fromAsset'
  },
  {
    text: '',
    value: 'isWorth',
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
    text: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
    value: 'usdPrice',
    align: 'end'
  },
  {
    text: '',
    value: 'actions',
    sortable: false
  }
]);

const router = useRouter();
const route = useRoute();
const { items, loading, refreshing, save, deletePrice, refresh } =
  useLatestPrices(filter, t);
const {
  setPostSubmitFunc,
  openDialog,
  setOpenDialog,
  submitting,
  closeDialog,
  setSubmitFunc,
  trySubmit
} = useLatestPriceForm();
const { show } = useConfirmStore();

const showDeleteConfirmation = (item: ManualPrice) => {
  show(
    {
      title: t('price_table.delete.dialog.title'),
      message: t('price_table.delete.dialog.message')
    },
    () => deletePrice(item)
  );
};

const openForm = (cPrice: ManualPrice | null = null) => {
  set(update, !!cPrice);
  if (cPrice) {
    set(price, {
      ...cPrice,
      price: cPrice.price.toFixed() ?? ''
    });
  } else {
    set(price, {
      ...emptyPrice(),
      fromAsset: get(filter) ?? ''
    });
  }
  setOpenDialog(true);
};

const hideForm = () => {
  closeDialog();
  set(price, emptyPrice());
};

onMounted(async () => {
  setSubmitFunc(() => save(get(price), get(update)));
  setPostSubmitFunc(refresh);
  startPromise(refresh());

  const query = get(route).query;

  if (query.add) {
    openForm();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout>
    <template #title>
      <span class="text-rui-text-secondary">
        {{ t('navigation_menu.manage_prices') }} /
      </span>
      {{ t('navigation_menu.manage_prices_sub.latest_prices') }}
    </template>

    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            color="primary"
            variant="outlined"
            :loading="loading || refreshing"
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
      <div class="mb-4 flex flex-row-reverse">
        <AssetSelect
          v-model="filter"
          class="max-w-[360px]"
          outlined
          include-nfts
          :label="t('price_management.from_asset')"
          clearable
          hide-details
        >
          <template #prepend>
            <RuiIcon size="20" name="filter-line" />
          </template>
        </AssetSelect>
      </div>
      <DataTable :items="items" :headers="headers" :loading="loading">
        <template #item.fromAsset="{ item }">
          <NftDetails
            v-if="isNft(item.fromAsset)"
            :identifier="item.fromAsset"
          />
          <AssetDetails v-else :asset="item.fromAsset" />
        </template>
        <template #item.toAsset="{ item }">
          <AssetDetails :asset="item.toAsset" />
        </template>
        <template #item.price="{ item }">
          <AmountDisplay :value="item.price" />
        </template>
        <template #item.isWorth>
          {{ t('price_table.is_worth') }}
        </template>
        <template #item.usdPrice="{ item }">
          <AmountDisplay
            v-if="item.usdPrice && item.usdPrice.gte(0)"
            show-currency="symbol"
            :price-asset="item.fromAsset"
            :price-of-asset="item.usdPrice"
            fiat-currency="USD"
            :value="item.usdPrice"
          />
          <div v-else class="flex justify-end">
            <VSkeletonLoader width="70" type="text" />
          </div>
        </template>
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
      <LatestPriceForm v-model="price" :edit="update" />
    </BigDialog>
  </TablePageLayout>
</template>
