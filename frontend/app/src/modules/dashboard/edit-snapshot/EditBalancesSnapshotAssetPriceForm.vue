<script setup lang="ts">
import type { ZodType } from 'zod';
import { useForm } from '@/modules/core/form/use-form';
import {
  type AssetPriceFormState,
  assetPriceSchema,
} from '@/modules/dashboard/edit-snapshot/snapshot-forms';
import { useSnapshotAssetPrice } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-price';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import TwoFieldsAmountInput from '@/modules/shell/components/inputs/TwoFieldsAmountInput.vue';

const amount = defineModel<string>('amount', { required: true });

const usdValue = defineModel<string>('usdValue', { required: true });

const asset = defineModel<string>('asset', { default: '', required: false });

const { disableAsset = false, nft = false, timestamp } = defineProps<{
  timestamp: number;
  disableAsset?: boolean;
  nft?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const schema = computed<ZodType>(() => assetPriceSchema({
  amount: t('dashboard.snapshot.edit.dialog.balances.rules.amount'),
  asset: t('dashboard.snapshot.edit.dialog.balances.rules.asset'),
  value: t('dashboard.snapshot.edit.dialog.balances.rules.value'),
}));

/**
 * Display only: this form exposes no `validate`, so nothing it reports can stop a save. The gate is
 * EditBalancesSnapshotForm's, over the category and location. Submitting here is a no-op too - the
 * price is persisted through `submitPrice`, not the form core.
 */
const form = useForm<AssetPriceFormState, AssetPriceFormState>({
  initial: (): AssetPriceFormState => ({ amount: get(amount), asset: get(asset), usdValue: get(usdValue) }),
  schema,
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): AssetPriceFormState => ({ ...state }),
});

// The price state machine writes back to the fields it derives, so it is given the form's state to
// drive rather than the parent's models, and the two are mirrored below.
const {
  modelAssetToFiatPrice,
  modelAssetToUsdPrice,
  currencySymbol,
  fetching,
  modelFiatValue,
  modelFiatValueFocused,
  isCurrentCurrencyUsd,
  reset,
  submitPrice,
} = useSnapshotAssetPrice({
  amount: toRef(form.state, 'amount'),
  asset: toRef(form.state, 'asset'),
  timestamp: () => timestamp,
  usdValue: toRef(form.state, 'usdValue'),
});

// Both directions write the value they were handed, so an echo settles rather than looping.
watchImmediate([amount, asset, usdValue], ([nextAmount, nextAsset, nextUsdValue]) => {
  form.state.amount = nextAmount;
  form.state.asset = nextAsset;
  form.state.usdValue = nextUsdValue;
});

watch(() => form.state, (state) => {
  set(amount, state.amount);
  set(asset, state.asset);
  set(usdValue, state.usdValue);
}, { deep: true });

defineExpose({
  reset,
  submitPrice,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <AssetSelect
        v-if="!nft"
        v-model="form.state.asset"
        outlined
        :disabled="disableAsset"
        :source="{ showIgnored: true }"
        data-testid="asset"
        :error-messages="disableAsset ? [''] : form.errors('asset')"
        @blur="form.touch('asset')"
      />
      <RuiTextField
        v-else
        v-model="form.state.asset"
        :label="t('common.asset')"
        variant="outlined"
        color="primary"
        :disabled="disableAsset"
        class="mb-1.5"
        :error-messages="disableAsset ? [''] : form.errors('asset')"
        :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        @blur="form.touch('asset')"
      />
      <AmountInput
        v-model="form.state.amount"
        variant="outlined"
        data-testid="amount"
        :label="t('common.amount')"
        :error-messages="form.errors('amount')"
        @blur="form.touch('amount')"
      />
    </div>
    <TwoFieldsAmountInput
      v-if="isCurrentCurrencyUsd"
      v-model:primary-value="modelAssetToUsdPrice"
      v-model:secondary-value="form.state.usdValue"
      class="mb-5"
      :loading="fetching"
      :disabled="fetching"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol,
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol,
        }),
      }"
      :error-messages="{
        primary: form.errors('usdValue'),
        secondary: form.errors('usdValue'),
      }"
      :hint="t('transactions.events.form.asset_price.hint')"
      @update:reversed="modelFiatValueFocused = $event"
    />

    <TwoFieldsAmountInput
      v-else
      v-model:primary-value="modelAssetToFiatPrice"
      v-model:secondary-value="modelFiatValue"
      class="mb-5"
      :loading="fetching"
      :disabled="fetching"
      :label="{
        primary: t('transactions.events.form.asset_price.label', {
          symbol: currencySymbol,
        }),
        secondary: t('common.value_in_symbol', {
          symbol: currencySymbol,
        }),
      }"
      @update:reversed="modelFiatValueFocused = $event"
    />
  </div>
</template>
