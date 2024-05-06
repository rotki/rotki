<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { ProfitLossEvent } from '@/types/reports';
import type { HistoricalPriceFormPayload } from '@/types/prices';

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

async function openEditHistoricPriceDialog() {
  set(showDialog, true);
  set(fetchingPrice, true);
  const { assetIdentifier, timestamp } = get(event);
  const historicPrice = await getHistoricPrice({
    fromAsset: assetIdentifier,
    toAsset: get(currency),
    timestamp,
  });
  set(price, historicPrice.isPositive() ? historicPrice.toFixed() : '0');
  set(fetchingPrice, false);
}

const datetime: ComputedRef<string> = computed(() =>
  convertFromTimestamp(get(event).timestamp),
);

const { t } = useI18n();

const rules = {
  price: {
    required: helpers.withMessage(
      t('price_form.price_non_empty').toString(),
      required,
    ),
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

async function updatePrice() {
  const payload: HistoricalPriceFormPayload = {
    fromAsset: get(event).assetIdentifier,
    toAsset: get(currency),
    timestamp: get(event).timestamp,
    price: get(price),
  };

  try {
    await addHistoricalPrice(payload);
    set(showDialog, false);
  }
  catch (error: any) {
    const values = { message: error.message };
    const title = t('price_management.add.error.title');
    const description = t('price_management.add.error.description', values);
    setMessage({
      title,
      description,
      success: false,
    });
  }
}
</script>

<template>
  <div class="flex justify-end">
    <RuiMenu
      :popper="{ placement: 'bottom-end' }"
    >
      <template #activator="{ on }">
        <RuiButton
          variant="text"
          class="!p-2"
          icon
          v-on="on"
        >
          <RuiIcon name="more-2-fill" />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          variant="list"
          @click="openEditHistoricPriceDialog()"
        >
          <template #prepend>
            <RuiIcon name="edit-line" />
          </template>
          {{ t('profit_loss_events.edit_historic_price') }}
        </RuiButton>
      </div>
    </RuiMenu>

    <RuiDialog
      v-model="showDialog"
      max-width="450px"
    >
      <AppBridge>
        <RuiCard>
          <template #header>
            {{ t('profit_loss_events.edit_historic_price') }}
          </template>

          <form class="flex flex-col gap-4">
            <AssetSelect
              :value="event.assetIdentifier"
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
      </AppBridge>
    </RuiDialog>
  </div>
</template>
