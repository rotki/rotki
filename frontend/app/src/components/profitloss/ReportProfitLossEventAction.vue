<script setup lang="ts">
import { useI18n } from 'vue-i18n-composable';
import { type ComputedRef, type Ref } from 'vue';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { type ProfitLossEvent } from '@/types/reports';
import { useBalancePricesStore } from '@/store/balances/prices';
import { convertFromTimestamp } from '@/utils/date';
import { useMessageStore } from '@/store/message';
import { type HistoricalPriceFormPayload } from '@/types/prices';

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

const datetime: ComputedRef<string> = computed(() => {
  return convertFromTimestamp(get(event).timestamp, true);
});

const { t, tc } = useI18n();

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
    const title = tc('price_management.add.error.title');
    const description = tc('price_management.add.error.description', 0, values);
    setMessage({
      title,
      description,
      success: false
    });
  }
};
</script>

<template>
  <div>
    <v-menu transition="slide-y-transaction" max-width="250px" offset-y>
      <template #activator="{ on }">
        <v-btn class="ml-1" icon v-on="on">
          <v-icon>mdi-dots-vertical</v-icon>
        </v-btn>
      </template>
      <v-list>
        <v-list-item link @click="openEditHistoricPriceDialog">
          <v-list-item-icon class="mr-4">
            <v-icon>mdi-pencil</v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            {{ tc('profit_loss_events.edit_historic_price') }}
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-menu>

    <v-dialog v-model="showDialog" max-width="450px">
      <card>
        <template #title>
          {{ tc('profit_loss_events.edit_historic_price') }}
        </template>

        <v-form class="mt-2">
          <v-row>
            <v-col cols="12">
              <asset-select
                :value="event.asset"
                :label="tc('price_form.from_asset')"
                hide-details
                disabled
                outlined
              />
            </v-col>

            <v-col cols="12">
              <asset-select
                :value="currency"
                :label="tc('price_form.to_asset')"
                hide-details
                disabled
                outlined
              />
            </v-col>

            <v-col cols="12">
              <date-time-picker
                :value="datetime"
                outlined
                disabled
                hide-details
                :label="tc('common.datetime')"
                seconds
              />
            </v-col>

            <v-col cols="12">
              <amount-input
                v-model="price"
                outlined
                :loading="fetchingPrice"
                :disabled="fetchingPrice"
                :label="tc('common.price')"
                :error-messages="v$.price.$errors.map(e => e.$message)"
              />
            </v-col>
          </v-row>
        </v-form>

        {{ tc('profit_loss_events.edit_price_warning') }}

        <template #buttons>
          <v-spacer />
          <v-btn depressed @click="showDialog = false">
            {{ tc('common.actions.cancel') }}
          </v-btn>
          <v-btn color="primary" @click="updatePrice">
            {{ tc('price_form.update_price') }}
          </v-btn>
        </template>
      </card>
    </v-dialog>
  </div>
</template>
