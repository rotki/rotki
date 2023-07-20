<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { convertToTimestamp } from '@/utils/date';
import { type HistoricalPriceFormPayload } from '@/types/prices';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  value: HistoricalPriceFormPayload;
  edit: boolean;
}>();

const emit = defineEmits<{
  (e: 'input', price: Partial<HistoricalPriceFormPayload>): void;
}>();

const { value } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

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

const { t } = useI18n();

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

const { valid, setValidation } = useHistoricPriceForm();

const v$ = setValidation(
  rules,
  {
    fromAsset: computed(() => get(value).fromAsset),
    toAsset: computed(() => get(value).toAsset),
    price,
    date
  },
  { $autoDirty: true }
);
</script>

<template>
  <VForm :value="valid">
    <VRow class="mt-2">
      <VCol cols="12" md="6">
        <AssetSelect
          :value="value.fromAsset"
          :label="t('price_form.from_asset')"
          outlined
          :disabled="edit"
          :error-messages="toMessages(v$.fromAsset)"
          @input="input({ fromAsset: $event })"
        />
      </VCol>
      <VCol cols="12" md="6">
        <AssetSelect
          :value="value.toAsset"
          :label="t('price_form.to_asset')"
          :disabled="edit"
          outlined
          :error-messages="toMessages(v$.toAsset)"
          @input="input({ toAsset: $event })"
        />
      </VCol>
    </VRow>
    <VRow>
      <VCol>
        <AmountInput
          v-model="price"
          outlined
          :error-messages="toMessages(v$.price)"
          :label="t('common.price')"
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
                <AmountDisplay :value="numericPrice" :tooltip="false" />
              </strong>
            </template>
          </i18n>
        </div>
      </VCol>
    </VRow>
    <VRow>
      <VCol>
        <DateTimePicker
          :value="date"
          outlined
          :label="t('common.datetime')"
          seconds
          :disabled="edit"
          :error-messages="toMessages(v$.date)"
          @input="input({ timestamp: convertToTimestamp($event) })"
        />
      </VCol>
    </VRow>
  </VForm>
</template>
