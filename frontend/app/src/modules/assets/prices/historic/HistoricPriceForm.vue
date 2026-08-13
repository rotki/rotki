<script setup lang="ts">
import type { ZodType } from 'zod';
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { historicPriceSchema } from '@/modules/assets/prices/price-forms';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { bigNumberifyFromRef } from '@/modules/core/common/data/bignumbers';
import { useModelForm } from '@/modules/core/form/use-model-form';
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

const numericPrice = bigNumberifyFromRef(() => form.state.price);

defineExpose({
  validate: (): boolean => form.validate(),
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <AssetSelect
        v-model="form.state.fromAsset"
        :label="t('price_form.from_asset')"
        outlined
        :disabled="editMode"
        :error-messages="form.errors('fromAsset')"
        data-testid="historic-price-from-asset"
        @update:model-value="form.touch('fromAsset')"
      />
      <AssetSelect
        v-model="form.state.toAsset"
        :label="t('price_form.to_asset')"
        :disabled="editMode"
        outlined
        :error-messages="form.errors('toAsset')"
        data-testid="historic-price-to-asset"
        @update:model-value="form.touch('toAsset')"
      />
    </div>
    <DateTimePicker
      v-model="form.state.timestamp"
      :label="t('common.datetime')"
      :disabled="editMode"
      type="epoch"
      variant="outlined"
      :error-messages="form.errors('timestamp')"
      data-testid="historic-price-datetime"
      @update:model-value="form.touch('timestamp')"
    />
    <AmountInput
      v-model="form.state.price"
      variant="outlined"
      :error-messages="form.errors('price')"
      :label="t('common.price')"
      data-testid="historic-price-value"
      @update:model-value="form.touch('price')"
    />
    <i18n-t
      v-if="form.state.price && fromAssetSymbol && toAssetSymbol"
      scope="global"
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
          <ValueDisplay
            :value="numericPrice"
            no-tooltip
          />
        </strong>
      </template>
    </i18n-t>
  </div>
</template>
