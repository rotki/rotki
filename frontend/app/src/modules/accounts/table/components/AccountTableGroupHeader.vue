<script setup lang="ts">
import { type BigNumber, toSentenceCase } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';

interface Props {
  category: string;
  categoryTotal: BigNumber;
  colspan: number;
  isOpen: boolean;
  isSectionLoading: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <td
    :id="category"
    class="py-2 px-2"
    :colspan="colspan - 2"
  >
    <div class="flex font-medium gap-2 items-center">
      <RuiButton
        icon
        variant="text"
        size="sm"
        @click="emit('toggle')"
      >
        <RuiIcon :name="isOpen ? 'lu-chevron-up' : 'lu-chevron-down'" />
      </RuiButton>
      <template v-if="category">
        {{ t('account_balances.data_table.group', { type: category === 'evm' ? 'EVM' : toSentenceCase(category) }) }}
      </template>
    </div>
  </td>
  <td class="text-end text-body-2 px-4 py-0">
    <AmountDisplay
      v-if="category"
      fiat-currency="USD"
      :value="categoryTotal"
      show-currency="symbol"
      :loading="isSectionLoading"
    />
  </td>
  <td />
</template>
