<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { ManualPriceFormPayload } from '@/types/prices';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useFormStateWatcher } from '@/composables/form';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';

const modelValue = defineModel<ManualPriceFormPayload>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

withDefaults(
  defineProps<{
    disableFromAsset?: boolean;
    editMode?: boolean;
  }>(),
  {
    disableFromAsset: false,
    editMode: false,
  },
);

const { assetSymbol } = useAssetInfoRetrieval();

const fromAsset = useRefPropVModel(modelValue, 'fromAsset');
const toAsset = useRefPropVModel(modelValue, 'toAsset');
const price = useRefPropVModel(modelValue, 'price');

const fromAssetSymbol = assetSymbol(fromAsset);
const toAssetSymbol = assetSymbol(toAsset);

const numericPrice = bigNumberifyFromRef(price);

const { t } = useI18n({ useScope: 'global' });

const rules = {
  fromAsset: {
    required: helpers.withMessage(t('price_form.from_non_empty'), required),
  },
  price: {
    required: helpers.withMessage(t('price_form.price_non_empty'), required),
  },
  toAsset: {
    required: helpers.withMessage(t('price_form.to_non_empty'), required),
  },
};

const states = {
  fromAsset,
  price,
  toAsset,
};

const v$ = useVuelidate(
  rules,
  states,
  { $autoDirty: true, $externalResults: errors },
);

useFormStateWatcher(states, stateUpdated);

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4">
      <AssetSelect
        v-model="fromAsset"
        :label="t('price_form.from_asset')"
        outlined
        include-nfts
        :disabled="editMode || disableFromAsset"
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
      scope="global"
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
  </div>
</template>
