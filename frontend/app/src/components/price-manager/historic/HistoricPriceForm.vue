<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { convertToTimestamp } from '@/utils/date';
import { toMessages } from '@/utils/validation';
import type { HistoricalPriceFormPayload } from '@/types/prices';

const props = defineProps<{
  modelValue: HistoricalPriceFormPayload;
  edit: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', price: Partial<HistoricalPriceFormPayload>): void;
}>();

const { assetSymbol } = useAssetInfoRetrieval();

const date = computed({
  get() {
    const timestamp = props.modelValue.timestamp;
    return timestamp ? convertFromTimestamp(timestamp) : '';
  },
  set(date: string) {
    emit('update:model-value', {
      ...props.modelValue,
      timestamp: convertToTimestamp(date),
    });
  },
});

const fromAsset = useSimplePropVModel(props, 'fromAsset', emit);
const toAsset = useSimplePropVModel(props, 'toAsset', emit);
const price = useSimplePropVModel(props, 'price', emit);

const fromAssetSymbol = assetSymbol(fromAsset);
const toAssetSymbol = assetSymbol(toAsset);

const numericPrice = bigNumberifyFromRef(price);

const { t } = useI18n();

const rules = {
  fromAsset: {
    required: helpers.withMessage(
      t('price_form.from_non_empty').toString(),
      required,
    ),
  },
  toAsset: {
    required: helpers.withMessage(
      t('price_form.to_non_empty').toString(),
      required,
    ),
  },
  price: {
    required: helpers.withMessage(
      t('price_form.price_non_empty').toString(),
      required,
    ),
  },
  date: {
    required: helpers.withMessage(
      t('price_form.date_non_empty').toString(),
      required,
    ),
  },
};

const { setValidation } = useHistoricPriceForm();

const v$ = setValidation(
  rules,
  {
    fromAsset,
    toAsset,
    price,
    date,
  },
  { $autoDirty: true },
);
</script>

<template>
  <form class="flex flex-col gap-4">
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <AssetSelect
        v-model="fromAsset"
        :label="t('price_form.from_asset')"
        outlined
        :disabled="edit"
        :error-messages="toMessages(v$.fromAsset)"
      />
      <AssetSelect
        v-model="toAsset"
        :label="t('price_form.to_asset')"
        :disabled="edit"
        outlined
        :error-messages="toMessages(v$.toAsset)"
      />
    </div>
    <AmountInput
      v-model="price"
      variant="outlined"
      :error-messages="toMessages(v$.price)"
      :label="t('common.price')"
    />
    <i18n-t
      v-if="price && fromAssetSymbol && toAssetSymbol"
      tag="div"
      keypath="price_form.historic.hint"
      class="text-caption text-rui-success -mt-9 pl-3"
    >
      <template #fromAsset>
        <strong>
          {{ fromAssetSymbol }}
        </strong>
      </template>
      <template #toAsset>
        <strong>
          {{ toAssetSymbol }}
        </strong>
      </template>
      <template #price>
        <strong>
          <AmountDisplay
            :value="numericPrice"
            :tooltip="false"
          />
        </strong>
      </template>
    </i18n-t>
    <DateTimePicker
      v-model="date"
      :label="t('common.datetime')"
      :disabled="edit"
      :error-messages="toMessages(v$.date)"
    />
  </form>
</template>
