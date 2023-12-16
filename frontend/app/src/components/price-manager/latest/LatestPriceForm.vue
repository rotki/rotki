<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';
import type { ManualPriceFormPayload } from '@/types/prices';

const props = withDefaults(
  defineProps<{
    modelValue: ManualPriceFormPayload;
    edit: boolean;
    disableFromAsset?: boolean;
  }>(),
  {
    disableFromAsset: false,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', price: Partial<ManualPriceFormPayload>): void;
}>();

const { assetSymbol } = useAssetInfoRetrieval();

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
};

const { setValidation } = useLatestPriceForm();

const v$ = setValidation(
  rules,
  {
    fromAsset,
    toAsset,
    price,
  },
  { $autoDirty: true },
);
</script>

<template>
  <form class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4">
      <AssetSelect
        v-model="fromAsset"
        :label="t('price_form.from_asset')"
        outlined
        include-nfts
        :disabled="edit || disableFromAsset"
        :error-messages="toMessages(v$.fromAsset)"
      />
      <AssetSelect
        v-model="toAsset"
        :label="t('price_form.to_asset')"
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
      keypath="price_form.latest.hint"
      class="text-caption text-rui-success -mt-7 pb-1 pl-3"
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
  </form>
</template>
