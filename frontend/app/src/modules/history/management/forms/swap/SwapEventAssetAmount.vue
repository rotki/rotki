<script setup lang="ts">
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import ToggleLocationLink from '@/modules/history/management/forms/common/ToggleLocationLink.vue';

const asset = defineModel<string>('asset', { required: true });
const amount = defineModel<string>('amount', { required: true });

defineProps<{
  type: 'receive' | 'spend';
  location: string | undefined;
  errorMessages: {
    asset: string[];
    amount: string[];
  };
}>();

const evmChain = ref<string>();

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
    <div class="flex">
      <AssetSelect
        v-model="asset"
        outlined
        clearable
        :evm-chain="evmChain"
        :data-cy="`${type}-asset`"
        :label="type === 'receive' ? t('swap_event_form.receive_asset') : t('swap_event_form.spend_asset')"
        :error-messages="errorMessages.asset"
      />
      <ToggleLocationLink
        v-model="evmChain"
        :location="location"
      />
    </div>
  </div>
</template>
