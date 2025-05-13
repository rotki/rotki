<script lang="ts" setup>
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import ToggleLocationLink from '@/modules/history/management/forms/common/ToggleLocationLink.vue';

const hasFee = defineModel<boolean>({ required: true });
const feeAsset = defineModel<string>('asset', { required: true });
const feeAmount = defineModel<string>('amount', { required: true });

defineProps<{
  location: string | undefined;
  errorMessages: {
    fee: string[];
    amount: string[];
  };
}>();

const evmChain = ref<string>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCheckbox
    v-model="hasFee"
    label="Has Fee"
    data-cy="has-fee"
    color="primary"
  />
  <div class="grid md:grid-cols-2 gap-4">
    <AmountInput
      v-model="feeAmount"
      clearable
      :disabled="!hasFee"
      variant="outlined"
      data-cy="fee-amount"
      :label="t('common.fee')"
      :error-messages="errorMessages.fee"
    />
    <div class="flex">
      <AssetSelect
        v-model="feeAsset"
        outlined
        :disabled="!hasFee"
        clearable
        data-cy="fee-asset"
        :label="t('transactions.events.form.fee_asset.label')"
        :error-messages="errorMessages.amount"
      />
      <ToggleLocationLink
        v-model="evmChain"
        :location="location"
      />
    </div>
  </div>
</template>
