<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { type ProfitLossEvent } from '@/types/reports';
import { type HistoricalPriceFormPayload } from '@/types/prices';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  event: ProfitLossEvent;
  currency: string;
}>();

const { event, currency } = toRefs(props);

const { getHistoricPrice } = useBalancePricesStore();
const { addHistoricalPrice } = useAssetPricesApi();

const fetchingPrice: Ref<boolean> = ref(false);
const showDialog: Ref<boolean> = ref(false);
const price: Ref<string> = ref('');

const openEditHistoricPriceDialog = async () => {
  set(showDialog, true);
  set(fetchingPrice, true);
  const { asset, timestamp } = get(event);
  const historicPrice = await getHistoricPrice({
    fromAsset: asset,
    toAsset: get(currency),
    timestamp
  });
  set(price, historicPrice.isPositive() ? historicPrice.toFixed() : '0');
  set(fetchingPrice, false);
};

const datetime: ComputedRef<string> = computed(() =>
  convertFromTimestamp(get(event).timestamp)
);

const { t } = useI18n();

const rules = {
  price: {
    required: helpers.withMessage(
      t('price_form.price_non_empty').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    price
  },
  { $autoDirty: true }
);

const { setMessage } = useMessageStore();
const updatePrice = async () => {
  const payload: HistoricalPriceFormPayload = {
    fromAsset: get(event).asset,
    toAsset: get(currency),
    timestamp: get(event).timestamp,
    price: get(price)
  };

  try {
    await addHistoricalPrice(payload);
    set(showDialog, false);
  } catch (e: any) {
    const values = { message: e.message };
    const title = t('price_management.add.error.title');
    const description = t('price_management.add.error.description', values);
    setMessage({
      title,
      description,
      success: false
    });
  }
};
</script>

<template>
  <div class="flex justify-end">
    <VMenu transition="slide-y-transaction" max-width="250px" offset-y>
      <template #activator="{ on }">
        <RuiButton variant="text" class="!p-2" icon v-on="on">
          <RuiIcon name="more-2-fill" />
        </RuiButton>
      </template>
      <VList>
        <RuiButton variant="list" @click="openEditHistoricPriceDialog()">
          <template #prepend>
            <RuiIcon name="edit-line" />
          </template>
          {{ t('profit_loss_events.edit_historic_price') }}
        </RuiButton>
      </VList>
    </VMenu>

    <VDialog v-model="showDialog" max-width="450px">
      <RuiCard>
        <template #header>
          {{ t('profit_loss_events.edit_historic_price') }}
        </template>

        <form class="flex flex-col gap-4">
          <AssetSelect
            :value="event.asset"
            :label="t('price_form.from_asset')"
            hide-details
            disabled
            outlined
          />
          <AssetSelect
            :value="currency"
            :label="t('price_form.to_asset')"
            hide-details
            disabled
            outlined
          />
          <DateTimePicker
            :value="datetime"
            outlined
            disabled
            hide-details
            :label="t('common.datetime')"
          />
          <AmountInput
            v-model="price"
            outlined
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
          <RuiButton variant="text" color="primary" @click="showDialog = false">
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton color="primary" @click="updatePrice()">
            {{ t('price_form.update_price') }}
          </RuiButton>
        </template>
      </RuiCard>
    </VDialog>
  </div>
</template>
