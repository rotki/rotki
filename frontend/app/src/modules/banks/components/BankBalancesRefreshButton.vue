<script setup lang="ts">
import type { BankConnectionIdentity } from '@/modules/banks/types';
import BankLabel from '@/modules/banks/components/BankLabel.vue';

const { banks, selected, loading = false } = defineProps<{
  banks: BankConnectionIdentity[];
  /** The bank the page shows; the button then refreshes only it. */
  selected?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  'refresh': [];
  'refresh-all': [];
  'refresh-bank': [bank: BankConnectionIdentity];
}>();

const { t } = useI18n({ useScope: 'global' });

const menuOpen = ref<boolean>(false);

const tooltip = computed<string>(() => selected
  ? t('bank_balances.refresh_menu.bank', { bank: selected })
  : t('bank_balances.refresh_menu.all'));

function refreshAll(): void {
  set(menuOpen, false);
  emit('refresh-all');
}

function refreshBank(bank: BankConnectionIdentity): void {
  set(menuOpen, false);
  emit('refresh-bank', bank);
}
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    color="primary"
  >
    <RuiTooltip
      :open-delay="400"
      :class-names="{ root: 'flex' }"
    >
      <template #activator>
        <RuiButton
          data-testid="refresh-bank-balances"
          :disabled="banks.length === 0"
          :loading="loading"
          @click="emit('refresh')"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
      </template>
      {{ tooltip }}
    </RuiTooltip>
    <RuiMenu
      v-model="menuOpen"
      :options="{ placement: 'bottom-end' }"
      :class-names="{ root: 'flex' }"
    >
      <template #activator="{ attrs }">
        <RuiButton
          v-bind="{
            ...attrs,
            'data-testid': 'refresh-bank-balances-menu',
          }"
          color="primary"
          variant="outlined"
          class="px-2"
          :disabled="banks.length === 0"
          :aria-label="t('bank_balances.refresh_menu.title')"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>

      <div class="w-72 max-w-full py-1">
        <RuiButton
          variant="list"
          :disabled="loading"
          data-testid="refresh-bank-menu-all"
          @click="refreshAll()"
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
          :key="`${bank.connector}#${bank.name}`"
          variant="list"
          :disabled="loading"
          :aria-label="t('bank_balances.refresh_menu.bank', { bank: bank.name })"
          data-testid="refresh-bank-menu-item"
          :data-bank="bank.name"
          @click="refreshBank(bank)"
        >
          <BankLabel
            :connector="bank.connector"
            :name="bank.name"
          />
        </RuiButton>
      </div>
    </RuiMenu>
  </RuiButtonGroup>
</template>
