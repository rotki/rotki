<script setup lang="ts">
import type { BankConnectionIdentity } from '@/modules/banks/types';
import BankLabel from '@/modules/banks/components/BankLabel.vue';
import RefreshSplitButton from '@/modules/shell/components/RefreshSplitButton.vue';

const { banks, selected, loading = false, isBankLoading } = defineProps<{
  banks: BankConnectionIdentity[];
  /** The bank the page shows; the button then refreshes only it. */
  selected?: string;
  /** Whether every bank is being refreshed. */
  loading?: boolean;
  isBankLoading: (identifier: string) => boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'refresh-all': [];
  'refresh-bank': [bank: BankConnectionIdentity];
}>();

const { t } = useI18n({ useScope: 'global' });

const buttonLoading = computed<boolean>(() => (selected ? isBankLoading(selected) : loading));

const tooltip = computed<string>(() => selected
  ? t('bank_balances.refresh_menu.bank', { bank: banks.find(bank => bank.identifier === selected)?.name ?? '' })
  : t('bank_balances.refresh_menu.all'));
</script>

<template>
  <RefreshSplitButton
    test-id="refresh-bank-balances"
    :menu-label="t('bank_balances.refresh_menu.title')"
    :tooltip="tooltip"
    :loading="buttonLoading"
    :disabled="banks.length === 0"
    :menu-disabled="banks.length === 0"
    @refresh="emit('refresh')"
  >
    <template #default="{ close }">
      <div class="w-72 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="loading"
          data-testid="refresh-bank-menu-all"
          @click="close(); emit('refresh-all')"
        >
          <template #prepend>
            <RuiIcon
              size="18"
              name="lu-refresh-ccw"
            />
          </template>
          {{ t('bank_balances.refresh_menu.all') }}
        </RuiButton>
        <RuiDivider class="my-1" />
        <div class="px-4 pt-1 pb-1 text-caption uppercase tracking-wide text-rui-text-secondary">
          {{ t('bank_balances.refresh_menu.section') }}
        </div>
        <RuiButton
          v-for="bank in banks"
          :key="bank.identifier"
          variant="list"
          :disabled="isBankLoading(bank.identifier)"
          :aria-label="t('bank_balances.refresh_menu.bank', { bank: bank.name })"
          data-testid="refresh-bank-menu-item"
          :data-bank="bank.name"
          @click="close(); emit('refresh-bank', bank)"
        >
          <BankLabel
            :connector="bank.connector"
            :name="bank.name"
          />
        </RuiButton>
      </div>
    </template>
  </RefreshSplitButton>
</template>
