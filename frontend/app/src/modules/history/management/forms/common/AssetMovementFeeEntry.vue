<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';

const hasFee = defineModel<boolean>('hasFee', { required: true });
const fee = defineModel<string>('fee', { required: true });
const feeAsset = defineModel<string>('feeAsset', { required: true });

const { errorMessages } = defineProps<{
  errorMessages: {
    fee: string[];
    feeAsset: string[];
  };
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <RuiCheckbox
      v-model="hasFee"
      data-cy="has-fee"
      label="Has Fee"
      color="primary"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="fee"
        :disabled="!hasFee"
        clearable
        variant="outlined"
        data-cy="fee-amount"
        :label="t('common.fee')"
        :error-messages="errorMessages.fee"
      />
      <AssetSelect
        v-model="feeAsset"
        :disabled="!hasFee"
        outlined
        clearable
        data-cy="fee-asset"
        :label="t('transactions.events.form.fee_asset.label')"
        :error-messages="errorMessages.feeAsset"
      />
    </div>
  </div>
</template>
