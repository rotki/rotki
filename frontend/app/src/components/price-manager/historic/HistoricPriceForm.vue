<template>
  <v-form v-model="valid">
    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <asset-select
          :value="value.fromAsset"
          :label="tc('price_form.from_asset')"
          outlined
          :disabled="edit"
          :rules="fromAssetRules"
          @input="input({ fromAsset: $event })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <asset-select
          :value="value.toAsset"
          :label="tc('price_form.to_asset')"
          :disabled="edit"
          outlined
          :rules="toAssetRules"
          @input="input({ toAsset: $event })"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <amount-input
          v-model="price"
          outlined
          :rules="priceRules"
          :label="tc('common.price')"
        />
        <div
          v-if="price && fromAsset && toAsset"
          class="text-caption green--text mt-n6 pb-1 pl-3"
        >
          <i18n tag="div" path="price_form.historic.hint">
            <template #fromAsset>
              <strong>
                {{ fromAsset }}
              </strong>
            </template>
            <template #toAsset>
              <strong>
                {{ toAsset }}
              </strong>
            </template>
            <template #price>
              <strong>
                <amount-display :value="numericPrice" :tooltip="false" />
              </strong>
            </template>
          </i18n>
        </div>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <date-time-picker
          :value="date"
          outlined
          :label="tc('common.datetime')"
          seconds
          :disabled="edit"
          :rules="dateRules"
          @input="input({ timestamp: convertToTimestamp($event) })"
        />
      </v-col>
    </v-row>
  </v-form>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { HistoricalPriceFormPayload } from '@/services/assets/types';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

const props = defineProps({
  value: {
    required: true,
    type: Object as PropType<HistoricalPriceFormPayload>
  },
  edit: {
    required: true,
    type: Boolean
  }
});

const emit = defineEmits(['input', 'valid']);

const { value } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const valid = ref(false);

const date = computed(({ value }) =>
  value.timestamp ? convertFromTimestamp(value.timestamp, true) : ''
);
const fromAsset = computed(({ value }) => get(assetSymbol(value.fromAsset)));
const toAsset = computed(({ value }) => get(assetSymbol(value.toAsset)));

const price = ref<string>('');
const numericPrice = bigNumberifyFromRef(price);

const input = (price: Partial<HistoricalPriceFormPayload>) => {
  emit('input', { ...get(value), ...price });
};

watch(valid, value => emit('valid', value));

watch(value, val => {
  set(price, val.price);
});

watch(price, val => {
  input({ price: val });
});

onMounted(() => {
  set(price, get(value).price);
});

const { t, tc } = useI18n();

const fromAssetRules = [
  (v: string) => !!v || t('price_form.from_non_empty').toString()
];
const toAssetRules = [
  (v: string) => !!v || t('price_form.to_non_empty').toString()
];
const priceRules = [
  (v: string) => !!v || t('price_form.price_non_empty').toString()
];
const dateRules = [
  (v: string) => !!v || t('price_form.date_non_empty').toString()
];
</script>
