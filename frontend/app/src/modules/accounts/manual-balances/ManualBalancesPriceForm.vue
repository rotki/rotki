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

defineExpose({
  savePrice,
});
</script>

<template>
  <div>
    <div
      v-if="fetchedPrice"
      class="flex items-center gap-2 mb-8 justify-center"
    >
      <div
        class="text-sm"
        :class="{ 'text-rui-text-secondary': isCustomPrice }"
      >
        {{ t('manual_balances_form.fields.use_fetched_price') }}
      </div>
      <RuiSwitch
        v-model="isCustomPrice"
        hide-details
        color="primary"
        class="-my-2"
        :disabled="pending || fetchingPrice"
      />
      <div
        class="text-sm"
        :class="{ 'text-rui-text-secondary': !isCustomPrice }"
      >
        {{ t('manual_balances_form.fields.input_manual_price') }}
      </div>
    </div>
    <div class="grid grid-cols-2 gap-y-2">
      <AmountInput
        v-model="price"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        variant="outlined"
        class="[&_fieldset]:!rounded-r-none"
        :label="t('common.price')"
      />
      <AssetSelect
        v-model="priceAsset"
        :disabled="fetchingPrice || !isCustomPrice || pending"
        :loading="fetchingPrice"
        variant="outlined"
        class="[&_fieldset]:!rounded-l-none"
        :hint="t('manual_balances_form.fields.price_asset_hint')"
        :label="t('manual_balances_form.fields.price_asset')"
      />
    </div>

    <div
      v-if="fiatPriceHint"
      class="-mt-4 mb-4 text-body-2 font-bold text-rui-success"
    >
      {{
        t('common.price_in_symbol', {
          symbol: currencySymbol,
        })
      }}:
      <FiatDisplay :value="fiatPriceHint" />
    </div>
  </div>
</template>
