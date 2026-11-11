<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ManualPriceFormPayload } from '@/modules/assets/prices/price-types';
import { latestPriceSchema } from '@/modules/assets/prices/price-forms';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useModelForm } from '@/modules/core/form/use-model-form';
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

const form = useModelForm<ManualPriceFormPayload>({
  model: modelValue,
  schema,
  stateUpdated,
});

const fromSymbol = useAssetField(() => form.state.fromAsset, 'symbol');
const fromName = useAssetField(() => form.state.fromAsset, 'name');
// an NFT has a name but no symbol
const fromAssetSymbol = computed<string>(() => get(fromSymbol) || get(fromName));
const toAssetSymbol = useAssetField(() => form.state.toAsset, 'symbol');

/** "1 XTZ is worth 0.62 EUR", as the price field's hint once all three are known; the price as typed. */
const priceHint = computed<string | undefined>(() => {
  const price = form.state.price;
  const from = get(fromAssetSymbol);
  const to = get(toAssetSymbol);
  if (!price || !from || !to)
    return undefined;
  return t('price_form.latest.hint', { fromAsset: from, price, toAsset: to });
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <AssetSelect
      v-model="form.state.fromAsset"
      :label="t('price_form.from_asset')"
      :source="{ nfts: 'include' }"
      :disabled="editMode || disableFromAsset"
      :error-messages="form.errors('fromAsset')"
      data-testid="latest-price-from-asset"
      @update:model-value="form.touch('fromAsset')"
    />
    <div class="grid grid-cols-2 gap-x-4">
      <AmountInput
        v-model="form.state.price"
        :error-messages="form.errors('price')"
        :hint="priceHint"
        :label="t('common.price')"
        data-testid="latest-price-value"
        @update:model-value="form.touch('price')"
      />
      <AssetSelect
        v-model="form.state.toAsset"
        :label="t('price_form.to_asset')"
        :error-messages="form.errors('toAsset')"
        data-testid="latest-price-to-asset"
        @update:model-value="form.touch('toAsset')"
      />
    </div>
  </div>
</template>
