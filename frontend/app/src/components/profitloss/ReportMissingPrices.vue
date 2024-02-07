<script setup lang="ts">
import { ApiValidationError } from '@/types/api/errors';
import type { BigNumber } from '@rotki/common';
import type { Ref } from 'vue';
import type { DataTableHeader } from '@/types/vuetify';
import type { EditableMissingPrice, MissingPrice } from '@/types/reports';
import type {
  HistoricalPrice,
  HistoricalPriceDeletePayload,
  HistoricalPriceFormPayload,
} from '@/types/prices';

const props = defineProps<{
  items: MissingPrice[];
  isPinned: boolean;
}>();

const { t } = useI18n();
const { items } = toRefs(props);
const prices = ref<HistoricalPrice[]>([]);
const errorMessages: Ref<Record<string, string[]>> = ref({});
const {
  fetchHistoricalPrices,
  addHistoricalPrice,
  editHistoricalPrice,
  deleteHistoricalPrice,
} = useAssetPricesApi();

function createKey(item: MissingPrice) {
  return item.fromAsset + item.toAsset + item.time;
}

async function getHistoricalPrices() {
  set(prices, await fetchHistoricalPrices());
}

onMounted(async () => {
  await getHistoricalPrices();
});

const refreshedHistoricalPrices: Ref<Record<string, BigNumber>> = ref({});

const formattedItems = computed<EditableMissingPrice[]>(() =>
  get(items).map((item) => {
    const savedHistoricalPrice = get(prices).find(
      price =>
        price.fromAsset === item.fromAsset
        && price.toAsset === item.toAsset
        && price.timestamp === item.time,
    );

    const key = createKey(item);
    const savedPrice = savedHistoricalPrice?.price;
    const refreshedHistoricalPrice = get(refreshedHistoricalPrices)[key];

    const useRefreshedHistoricalPrice
      = !savedPrice && !!refreshedHistoricalPrice;

    const price
      = (useRefreshedHistoricalPrice
        ? refreshedHistoricalPrice
        : savedPrice
      )?.toFixed() ?? '';

    return {
      ...item,
      saved: !!savedPrice,
      price,
      useRefreshedHistoricalPrice,
    };
  }),
);

async function updatePrice(item: EditableMissingPrice) {
  if (item.useRefreshedHistoricalPrice)
    return;

  const payload: HistoricalPriceDeletePayload = {
    fromAsset: item.fromAsset,
    toAsset: item.toAsset,
    timestamp: item.time,
  };

  try {
    if (item.price) {
      const formPayload: HistoricalPriceFormPayload = {
        ...payload,
        price: item.price,
      };

      if (item.saved)
        await editHistoricalPrice(formPayload);
      else
        await addHistoricalPrice(formPayload);
    }
    else if (item.saved) {
      await deleteHistoricalPrice(payload);
    }
  }
  catch (error: any) {
    let errorMessage = error.message;
    if (error instanceof ApiValidationError) {
      const errors = error.getValidationErrors({ price: '' });
      errorMessage = typeof errors === 'string' ? error.message : errors.price[0];
    }

    set(errorMessages, {
      ...get(errorMessages),
      [createKey(item)]: errorMessage,
    });
  }

  await getHistoricalPrices();
}

const tableRef = ref<any>(null);

const tableContainer = computed(() => get(tableRef)?.$el);

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t(
      'profit_loss_report.actionable.missing_prices.headers.from_asset',
    ).toString(),
    value: 'fromAsset',
  },
  {
    text: t(
      'profit_loss_report.actionable.missing_prices.headers.to_asset',
    ).toString(),
    value: 'toAsset',
  },
  {
    text: t('common.datetime').toString(),
    value: 'time',
  },
  {
    text: t('common.price').toString(),
    value: 'price',
    sortable: false,
  },
]);

const { getHistoricPrice } = useBalancePricesStore();

const refreshing = ref<boolean>(false);

async function refreshHistoricalPrice(item: EditableMissingPrice) {
  set(refreshing, true);
  const rateFromHistoricPrice = await getHistoricPrice({
    timestamp: item.time,
    fromAsset: item.fromAsset,
    toAsset: item.toAsset,
  });

  const key = createKey(item);
  if (rateFromHistoricPrice && rateFromHistoricPrice.gt(0)) {
    const refreshedHistoricalPricesVal = get(refreshedHistoricalPrices);
    refreshedHistoricalPricesVal[key] = rateFromHistoricPrice;
    set(refreshedHistoricalPrices, refreshedHistoricalPricesVal);
  }
  else {
    set(errorMessages, {
      ...get(errorMessages),
      [key]: t('profit_loss_report.actionable.missing_prices.price_not_found'),
    });
  }
  set(refreshing, false);
}

const css = useCssModule();
</script>

<template>
  <div>
    <DataTable
      ref="tableRef"
      class="table-inside-dialog"
      :class="{
        [css['table--pinned']]: isPinned,
      }"
      :headers="headers"
      :items="formattedItems"
      :container="tableContainer"
      :dense="isPinned"
      disable-floating-header
      flat
    >
      <template #item="{ item }">
        <tr :key="createKey(item)">
          <td>
            <AssetDetails
              link
              :asset="item.fromAsset"
            />
          </td>
          <td :class="isPinned ? 'px-2' : ''">
            <AssetDetails
              link
              :asset="item.toAsset"
            />
          </td>
          <td :class="isPinned ? 'px-2' : ''">
            <DateDisplay :timestamp="item.time" />
          </td>
          <td
            class="pb-1"
            :class="isPinned ? '!p-2' : 'py-3'"
          >
            <AmountInput
              v-model="item.price"
              :class="css.input"
              dense
              :disabled="item.useRefreshedHistoricalPrice"
              :label="
                t('profit_loss_report.actionable.missing_prices.input_price')
              "
              variant="outlined"
              :success-messages="
                item.saved
                  ? [
                    t(
                      'profit_loss_report.actionable.missing_prices.price_is_saved',
                    ),
                  ]
                  : []
              "
              :error-messages="errorMessages[createKey(item)]"
              @focus="delete errorMessages[createKey(item)]"
              @input="delete errorMessages[createKey(item)]"
              @blur="updatePrice(item)"
            >
              <template #append>
                <RuiTooltip
                  v-if="item.rateLimited"
                  :popper="{ placement: 'top' }"
                  :open-delay="400"
                  tooltip-class="max-w-[16rem]"
                  :disabled="refreshing"
                >
                  <template #activator>
                    <RuiButton
                      :disabled="!!item.price || refreshing"
                      :loading="refreshing"
                      class="-mr-3 !py-[0.625rem] rounded-l-none"
                      size="sm"
                      color="primary"
                      @click="refreshHistoricalPrice(item)"
                    >
                      <RuiIcon
                        size="20"
                        name="refresh-line"
                      />
                    </RuiButton>
                  </template>
                  <span>
                    {{
                      t(
                        'profit_loss_report.actionable.missing_prices.refresh_price_hint',
                      )
                    }}
                  </span>
                </RuiTooltip>
              </template>
            </AmountInput>
          </td>
        </tr>
      </template>
    </DataTable>
    <slot
      name="actions"
      :items="formattedItems"
    />
  </div>
</template>

<style module lang="scss">
.table {
  &--pinned {
    max-height: 100%;
    height: calc(100vh - 250px);
  }
}

.input {
  min-width: 120px;
}
</style>
