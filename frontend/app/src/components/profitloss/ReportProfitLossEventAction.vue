<script setup lang="ts">
import type { HistoricalPriceFormPayload } from '@/types/prices';
import type { ProfitLossEvent } from '@/types/reports';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useMessageStore } from '@/store/message';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { convertFromTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';

const props = defineProps<{
  event: ProfitLossEvent;
  currency: string;
}>();

const { currency, event } = toRefs(props);

const { resetHistoricalPricesData } = useHistoricCachePriceStore();
const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();

const fetchingPrice = ref<boolean>(false);
const showDialog = ref<boolean>(false);
const price = ref<string>('');

async function openEditHistoricPriceDialog() {
  set(showDialog, true);
  set(fetchingPrice, true);
  const { assetIdentifier, timestamp } = get(event);
  const historicPrice = await getHistoricPrice({
    fromAsset: assetIdentifier,
    timestamp,
    toAsset: get(currency),
  });
  set(price, historicPrice.isPositive() ? historicPrice.toFixed() : '0');
  set(fetchingPrice, false);
}

const datetime = computed<string>(() => convertFromTimestamp(get(event).timestamp));

const { t } = useI18n();

const rules = {
  price: {
    required: helpers.withMessage(t('price_form.price_non_empty'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    price,
  },
  { $autoDirty: true },
);

const { setMessage } = useMessageStore();

async function savePrice(payload: HistoricalPriceFormPayload) {
  await addHistoricalPrice(payload);
  resetHistoricalPricesData([payload]);
}

async function updatePrice() {
  const payload: HistoricalPriceFormPayload = {
    fromAsset: get(event).assetIdentifier,
    price: get(price),
    timestamp: get(event).timestamp,
    toAsset: get(currency),
  };

  try {
    await savePrice(payload);
    set(showDialog, false);
  }
  catch (error: any) {
    const values = { message: error.message };
    const title = t('price_management.add.error.title');
    const description = t('price_management.add.error.description', values);
    setMessage({
      description,
      success: false,
      title,
    });
  }
}
</script>

<template>
  <div class="flex justify-end">
    <RuiMenu :popper="{ placement: 'bottom-end' }">
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          class="!p-2"
          icon
          v-bind="attrs"
        >
          <RuiIcon name="lu-ellipsis-vertical" />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          variant="list"
          @click="openEditHistoricPriceDialog()"
        >
          <template #prepend>
            <RuiIcon name="lu-pencil-line" />
          </template>
          {{ t('profit_loss_events.edit_historic_price') }}
        </RuiButton>
      </div>
    </RuiMenu>

    <RuiDialog
      v-model="showDialog"
      max-width="450px"
    >
      <RuiCard>
        <template #header>
          {{ t('profit_loss_events.edit_historic_price') }}
        </template>

        <form class="flex flex-col gap-4">
          <AssetSelect
            :model-value="event.assetIdentifier"
            :label="t('price_form.from_asset')"
            hide-details
            disabled
            outlined
          />
          <AssetSelect
            :model-value="currency"
            :label="t('price_form.to_asset')"
            hide-details
            disabled
            outlined
          />
          <DateTimePicker
            :model-value="datetime"
            disabled
            hide-details
            :label="t('common.datetime')"
          />
          <AmountInput
            v-model="price"
            variant="outlined"
            :loading="fetchingPrice"
            :disabled="fetchingPrice"
            :label="t('common.price')"
            :error-messages="toMessages(v$.price)"
          />
        </form>

        <div class="text-body-2 text-rui-text-secondary">
          {{ t('profit_loss_events.edit_price_warning') }}
        </div>

        <template #footer>
          <div class="grow" />
          <RuiButton
            variant="text"
            color="primary"
            @click="showDialog = false"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            color="primary"
            @click="updatePrice()"
          >
            {{ t('price_form.update_price') }}
          </RuiButton>
        </template>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
