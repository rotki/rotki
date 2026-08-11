<script setup lang="ts">
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const hasFee = defineModel<boolean>('hasFee', { required: true });
const fee = defineModel<string>('fee', { required: true });
const feeAsset = defineModel<string>('feeAsset', { required: true });

const { errorMessages } = defineProps<{
  errorMessages: {
    fee: string[];
    feeAsset: string[];
  };
}>();

const emit = defineEmits<{
  blur: [field: 'fee' | 'feeAsset'];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div>
    <RuiCheckbox
      v-model="hasFee"
      data-testid="has-fee"
      :label="t('transactions.events.form.has_fee.label')"
      color="primary"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="fee"
        :disabled="!hasFee"
        clearable
        variant="outlined"
        data-testid="fee-amount"
        :label="t('common.fee')"
        :error-messages="errorMessages.fee"
        @blur="emit('blur', 'fee')"
      />
      <AssetSelect
        v-model="feeAsset"
        :disabled="!hasFee"
        outlined
        clearable
        data-testid="fee-asset"
        :label="t('transactions.events.form.fee_asset.label')"
        :error-messages="errorMessages.feeAsset"
        @blur="emit('blur', 'feeAsset')"
      />
    </div>
  </div>
</template>
