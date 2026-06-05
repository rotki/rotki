<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { toMessages } from '@/modules/core/common/validation/validation';
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

const {
  assetToFiatPrice,
  assetToUsdPrice,
  currencySymbol,
  fetching,
  fiatValue,
  fiatValueFocused,
  isCurrentCurrencyUsd,
  reset,
  submitPrice,
} = useSnapshotAssetPrice({ amount, asset, timestamp: () => timestamp, usdValue });

const rules = {
  amount: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.amount'), required),
  },
  asset: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.asset'), required),
  },
  usdValue: {
    required: helpers.withMessage(t('dashboard.snapshot.edit.dialog.balances.rules.value'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    amount,
    asset,
    usdValue,
  },
  {
    $autoDirty: true,
  },
);

defineExpose({
  reset,
  submitPrice,
});
</script>

<template>
  <div>
    <div
      v-if="v$"
      class="grid md:grid-cols-2 gap-4 mb-4"
    >
      <AssetSelect
        v-if="!nft"
        v-model="asset"
        outlined
        :disabled="disableAsset"
        show-ignored
        data-cy="asset"
        :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
        @blur="v$.asset.$touch()"
      />
      <RuiTextField
        v-else
        v-model="asset"
        :label="t('common.asset')"
        variant="outlined"
        color="primary"
        :disabled="disableAsset"
        class="mb-1.5"
        :error-messages="disableAsset ? [''] : toMessages(v$.asset)"
        :hint="t('dashboard.snapshot.edit.dialog.balances.nft_hint')"
        @blur="v$.asset.$touch()"
      />
      <AmountInput
        v-model="amount"
        variant="outlined"
        data-cy="amount"
        :label="t('common.amount')"
        :error-messages="toMessages(v$.amount)"
        @blur="v$.amount.$touch()"
      />
    </div>
    <TwoFieldsAmountInput
      v-if="isCurrentCurrencyUsd"
      v-model:primary-value="assetToUsdPrice"
      v-model:secondary-value="usdValue"
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
        primary: toMessages(v$.usdValue),
        secondary: toMessages(v$.usdValue),
      }"
      :hint="t('transactions.events.form.asset_price.hint')"
      @update:reversed="fiatValueFocused = $event"
    />

    <TwoFieldsAmountInput
      v-else
      v-model:primary-value="assetToFiatPrice"
      v-model:secondary-value="fiatValue"
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
      @update:reversed="fiatValueFocused = $event"
    />
  </div>
</template>
