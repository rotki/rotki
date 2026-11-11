<script setup lang="ts">
import type { ZodType } from 'zod';
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { historicPriceSchema } from '@/modules/assets/prices/price-forms';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useModelForm } from '@/modules/core/form/use-model-form';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const modelValue = defineModel<HistoricalPriceFormPayload>({ required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { editMode = false } = defineProps<{
  editMode?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useAssetField } = useAssetInfoRetrieval();

const schema = computed<ZodType>(() => historicPriceSchema({
  date: t('price_form.date_non_empty'),
  fromAsset: t('price_form.from_non_empty'),
  price: t('price_form.price_non_empty'),
  toAsset: t('price_form.to_non_empty'),
}));

const form = useModelForm<HistoricalPriceFormPayload>({
  model: modelValue,
  schema,
  stateUpdated,
  // Carried for the payload, never edited here, so it must not make the form look edited either.
  transientKeys: ['sourceType'],
});

const fromAssetSymbol = useAssetField(computed<string>(() => form.state.fromAsset), 'symbol');
const toAssetSymbol = useAssetField(computed<string>(() => form.state.toAsset), 'symbol');

/** "1 XTZ was worth 0.95 EUR", as the price field's hint once all three are known; the price as typed. */
const priceHint = computed<string | undefined>(() => {
  const price = form.state.price;
  const from = get(fromAssetSymbol);
  const to = get(toAssetSymbol);
  if (!price || !from || !to)
    return undefined;
  return t('price_form.historic.hint', { fromAsset: from, price, toAsset: to });
});

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <dl
      v-if="editMode"
      class="grid grid-cols-3 gap-4 m-0 mb-4 rounded-rui-control border border-rui-divider px-4 py-3"
      data-testid="historic-price-summary"
    >
      <div class="flex flex-col gap-1 min-w-0">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('price_form.from_asset') }}
        </dt>
        <dd class="m-0 font-medium text-rui-text truncate">
          {{ fromAssetSymbol || form.state.fromAsset }}
        </dd>
      </div>
      <div class="flex flex-col gap-1 min-w-0">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('price_form.to_asset') }}
        </dt>
        <dd class="m-0 font-medium text-rui-text truncate">
          {{ toAssetSymbol || form.state.toAsset }}
        </dd>
      </div>
      <div class="flex flex-col gap-1">
        <dt class="text-sm font-medium text-rui-text-secondary">
          {{ t('common.datetime') }}
        </dt>
        <dd class="m-0 text-rui-text">
          <DateDisplay :timestamp="form.state.timestamp" />
        </dd>
      </div>
    </dl>
    <template v-else>
      <div class="grid md:grid-cols-2 gap-x-4 gap-y-1">
        <AssetSelect
          v-model="form.state.fromAsset"
          :label="t('price_form.from_asset')"
          :error-messages="form.errors('fromAsset')"
          data-testid="historic-price-from-asset"
          @update:model-value="form.touch('fromAsset')"
        />
        <AssetSelect
          v-model="form.state.toAsset"
          :label="t('price_form.to_asset')"
          :error-messages="form.errors('toAsset')"
          data-testid="historic-price-to-asset"
          @update:model-value="form.touch('toAsset')"
        />
      </div>
      <DateTimePicker
        v-model="form.state.timestamp"
        :label="t('common.datetime')"
        type="epoch"
        :error-messages="form.errors('timestamp')"
        data-testid="historic-price-datetime"
        @update:model-value="form.touch('timestamp')"
      />
    </template>
    <AmountInput
      v-model="form.state.price"
      :error-messages="form.errors('price')"
      :hint="priceHint"
      :label="t('common.price')"
      data-testid="historic-price-value"
      @update:model-value="form.touch('price')"
    />
  </div>
</template>
