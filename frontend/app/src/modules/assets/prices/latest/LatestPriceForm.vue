<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { isEqual } from 'es-toolkit';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { latestPriceSchema } from '@/modules/assets/prices/price-forms';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { bigNumberifyFromRef } from '@/modules/core/common/data/bignumbers';
import { useForm } from '@/modules/core/form/use-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const modelValue = defineModel<ManualPriceFormPayload>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { disableFromAsset = false, editMode = false } = defineProps<{
  disableFromAsset?: boolean;
  editMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useAssetField } = useAssetInfoRetrieval();

const schema = computed<ZodType>(() => latestPriceSchema({
  fromAsset: t('price_form.from_non_empty'),
  price: t('price_form.price_non_empty'),
  toAsset: t('price_form.to_non_empty'),
}));

/** The dialog owns the persist and reads the payload off the model, so submitting here is a no-op. */
const form = useForm<ManualPriceFormPayload, ManualPriceFormPayload>({
  initial: (): ManualPriceFormPayload => ({ ...get(modelValue) }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): ManualPriceFormPayload => ({ ...state }),
});

const fromAssetSymbol = useAssetField(computed<string>(() => form.state.fromAsset), 'symbol');
const toAssetSymbol = useAssetField(computed<string>(() => form.state.toAsset), 'symbol');

const numericPrice = bigNumberifyFromRef(() => form.state.price);

// The dialog reads the payload it saves straight off the model, so every edit is written back to it.
watch(() => form.state, (state) => {
  set(modelValue, { ...state });
}, { deep: true });

// And an edit made outside the form (a different row, a reset) is pulled back in.
watch(modelValue, (value) => {
  if (!isEqual(value, form.state))
    Object.assign(form.state, value);
}, { deep: true });

watch(form.dirty, (dirty) => {
  set(stateUpdated, dirty);
});

// The dialog keeps its prompt-on-close flag across opens, so hand it back disarmed.
onUnmounted(() => {
  set(stateUpdated, false);
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="grid md:grid-cols-2 gap-x-4">
      <AssetSelect
        v-model="form.state.fromAsset"
        :label="t('price_form.from_asset')"
        outlined
        include-nfts
        :disabled="editMode || disableFromAsset"
        :error-messages="form.errors('fromAsset')"
        data-testid="latest-price-from-asset"
        @update:model-value="form.touch('fromAsset')"
      />
      <AssetSelect
        v-model="form.state.toAsset"
        :label="t('price_form.to_asset')"
        outlined
        :error-messages="form.errors('toAsset')"
        data-testid="latest-price-to-asset"
        @update:model-value="form.touch('toAsset')"
      />
    </div>
    <AmountInput
      v-model="form.state.price"
      variant="outlined"
      :error-messages="form.errors('price')"
      :label="t('common.price')"
      data-testid="latest-price-value"
      @update:model-value="form.touch('price')"
    />
    <i18n-t
      v-if="form.state.price && fromAssetSymbol && toAssetSymbol"
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
          <ValueDisplay
            :value="numericPrice"
            no-tooltip
          />
        </strong>
      </template>
    </i18n-t>
  </div>
</template>
