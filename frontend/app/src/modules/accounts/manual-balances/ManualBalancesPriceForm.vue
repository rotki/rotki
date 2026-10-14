<script setup lang="ts">
import { useManualBalancePrice } from '@/modules/accounts/manual-balances/use-manual-balance-price';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useSetting } from '@/modules/settings/use-setting';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const { asset = '', pending } = defineProps<{
  pending: boolean;
  asset?: string;
}>();

const currencySymbol = useSetting('currencySymbol');

const {
  fetchedPrice,
  fetchingPrice,
  fiatPriceHint,
  modelIsCustomPrice: isCustomPrice,
  modelPrice: price,
  modelPriceAsset: priceAsset,
  savePrice,
} = useManualBalancePrice(() => asset, currencySymbol);

const { t } = useI18n({ useScope: 'global' });

const priceSource = computed<'fetched' | 'manual'>({
  get: () => get(isCustomPrice) ? 'manual' : 'fetched',
  set: (source: 'fetched' | 'manual') => set(isCustomPrice, source === 'manual'),
});

defineExpose({
  savePrice,
});
</script>

<template>
  <div class="flex flex-col gap-2">
    <RuiButtonGroup
      v-if="fetchedPrice"
      v-model="priceSource"
      variant="segmented"
      required
      size="sm"
      class="self-start"
      data-testid="manual-balances-form-price-source"
      :disabled="pending || fetchingPrice"
    >
      <RuiButton model-value="fetched">
        {{ t('manual_balances_form.fields.use_fetched_price') }}
      </RuiButton>
      <RuiButton model-value="manual">
        {{ t('manual_balances_form.fields.input_manual_price') }}
      </RuiButton>
    </RuiButtonGroup>
    <div class="grid grid-cols-2 gap-x-4">
      <AmountInput
        v-model="price"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        :label="t('common.price')"
      />
      <AssetSelect
        v-model="priceAsset"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        :hint="t('manual_balances_form.fields.price_asset_hint')"
        :label="t('manual_balances_form.fields.price_asset')"
      />
    </div>
    <div
      v-if="fiatPriceHint"
      class="-mt-4 text-caption text-rui-text-secondary"
      data-testid="manual-balances-form-fiat-price"
    >
      {{ t('common.price_in_symbol', { symbol: currencySymbol }) }}:
      <FiatDisplay :value="fiatPriceHint" />
    </div>
  </div>
</template>
