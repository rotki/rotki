<script setup lang="ts">
import type { SwapFeeState } from '@/modules/history/management/forms/swap-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

/** Mutated in place, so the form's touched state stays with the row across a removal. */
const modelValue = defineModel<SwapFeeState>({ required: true });

const { disabled, location } = defineProps<{
  index: number;
  disabled?: boolean;
  single: boolean;
  location?: string;
  errorMessages: {
    amount: string[];
    asset: string[];
  };
}>();

const emit = defineEmits<{
  remove: [index: number];
  blur: [field: 'amount' | 'asset'];
}>();

const { t } = useI18n({ useScope: 'global' });

const chain = ref<string>();

watchImmediate(() => location, (newLocation) => {
  if (newLocation)
    set(chain, newLocation);
});
</script>

<template>
  <div class="group/fee">
    <div class="flex items-center gap-4">
      <template v-if="!single">
        <div
          class="group-hover/fee:hidden font-medium border border-rui-grey-300 dark:border-rui-grey-800 rounded-full size-10 flex items-center justify-center -mt-5"
        >
          {{ index + 1 }}
        </div>
        <RuiButton
          class="hidden group-hover/fee:flex size-10 -mt-5"
          variant="outlined"
          :disabled="disabled"
          data-cy="fee-remove"
          icon
          color="error"
          @click="emit('remove', index)"
        >
          <RuiIcon
            name="lu-trash-2"
            size="14"
          />
        </RuiButton>
      </template>

      <div class="grow grid md:grid-cols-2 gap-4">
        <AmountInput
          v-model="modelValue.amount"
          variant="outlined"
          data-cy="fee-amount"
          :disabled="disabled"
          :label="t('common.amount')"
          :error-messages="errorMessages.amount"
          @blur="emit('blur', 'amount')"
        />
        <AssetSelect
          v-model="modelValue.asset"
          outlined
          show-ignored
          :disabled="disabled"
          data-cy="fee-asset"
          :chain="chain"
          :error-messages="errorMessages.asset"
          @blur="emit('blur', 'asset')"
        />
      </div>
    </div>
  </div>
</template>
