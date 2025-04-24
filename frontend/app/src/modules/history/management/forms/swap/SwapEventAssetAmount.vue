<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';

const asset = defineModel<string>('asset', { required: true });
const amount = defineModel<string>('amount', { required: true });

defineProps<{
  type: 'receive' | 'spend';
  errorMessages: {
    asset: string[];
    amount: string[];
  };
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid md:grid-cols-2 gap-4">
    <AmountInput
      v-model="amount"
      clearable
      variant="outlined"
      :data-cy="`${type}-amount`"
      :label="type === 'receive' ? t('swap_event_form.receive_amount') : t('swap_event_form.spend_amount') "
      :error-messages="errorMessages.amount"
    />
    <AssetSelect
      v-model="asset"
      outlined
      clearable
      :data-cy="`${type}-asset`"
      :label="type === 'receive' ? t('swap_event_form.receive_asset') : t('swap_event_form.spend_asset')"
      :error-messages="errorMessages.asset"
    />
  </div>
</template>
