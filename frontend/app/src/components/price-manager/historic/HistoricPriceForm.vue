<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { type PropType } from 'vue';
import { type HistoricalPriceFormPayload } from '@/services/assets/types';
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
const { assetSymbol } = useAssetInfoRetrievalStore();

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

const rules = {
  fromAsset: {
    required: helpers.withMessage(
      t('price_form.from_non_empty').toString(),
      required
    )
  },
  toAsset: {
    required: helpers.withMessage(
      t('price_form.to_non_empty').toString(),
      required
    )
  },
  price: {
    required: helpers.withMessage(
      t('price_form.price_non_empty').toString(),
      required
    )
  },
  date: {
    required: helpers.withMessage(
      t('price_form.date_non_empty').toString(),
      required
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    fromAsset: computed(() => get(value).fromAsset),
    toAsset: computed(() => get(value).toAsset),
    price,
    date
  },
  { $autoDirty: true }
);

watch(v$, ({ $invalid }) => {
  emit('valid', !$invalid);
});
</script>

<template>
  <v-form :value="!v$.$invalid">
    <v-row class="mt-2">
      <v-col cols="12" md="6">
        <asset-select
          :value="value.fromAsset"
          :label="tc('price_form.from_asset')"
          outlined
          :disabled="edit"
          :error-messages="v$.fromAsset.$errors.map(e => e.$message)"
          @input="input({ fromAsset: $event })"
        />
      </v-col>
      <v-col cols="12" md="6">
        <asset-select
          :value="value.toAsset"
          :label="tc('price_form.to_asset')"
          :disabled="edit"
          outlined
          :error-messages="v$.toAsset.$errors.map(e => e.$message)"
          @input="input({ toAsset: $event })"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <amount-input
          v-model="price"
          outlined
          :error-messages="v$.price.$errors.map(e => e.$message)"
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
          :error-messages="v$.date.$errors.map(e => e.$message)"
          @input="input({ timestamp: convertToTimestamp($event) })"
        />
      </v-col>
    </v-row>
  </v-form>
</template>
