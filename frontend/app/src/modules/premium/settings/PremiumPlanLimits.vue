<script setup lang="ts">
import { useCountFormatter } from '@/modules/assets/amount-display/use-count-formatter';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

interface PlanLimit {
  key: string;
  label: string;
  value: string;
}

const { t } = useI18n({ useScope: 'global' });

const { capabilities } = storeToRefs(usePremiumStore());
const { formatCount } = useCountFormatter();

/** What the plan allows, from the capabilities the server sends; a limit it leaves out is not shown. */
const limits = computed<PlanLimit[]>(() => {
  const caps = get(capabilities);
  if (!caps)
    return [];

  const entries: [key: string, label: string, value: string | undefined][] = [
    ['devices', t('premium_settings.limits.devices'), caps.limitOfDevices === undefined ? undefined : formatCount(caps.limitOfDevices)],
    ['backup', t('premium_settings.limits.backup'), caps.maxBackupSizeMb === undefined ? undefined : t('premium_settings.limits.backup_value', { size: formatCount(caps.maxBackupSizeMb) })],
    ['history', t('premium_settings.limits.history_events'), caps.historyEventsLimit === undefined ? undefined : formatCount(caps.historyEventsLimit)],
    ['pnl', t('premium_settings.limits.pnl_events'), caps.pnlEventsLimit === undefined ? undefined : formatCount(caps.pnlEventsLimit)],
    ['reports', t('premium_settings.limits.reports'), caps.reportsLookupLimit === undefined ? undefined : formatCount(caps.reportsLookupLimit)],
    ['staking', t('premium_settings.limits.eth_staked'), caps.ethStakedLimit === undefined ? undefined : t('premium_settings.limits.eth_staked_value', { amount: formatCount(caps.ethStakedLimit) })],
  ];

  return entries
    .filter((entry): entry is [string, string, string] => entry[2] !== undefined)
    .map(([key, label, value]) => ({ key, label, value }));
});
</script>

<template>
  <dl
    v-if="limits.length > 0"
    class="m-0 grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4"
    data-testid="premium-plan-limits"
  >
    <div
      v-for="limit in limits"
      :key="limit.key"
      class="flex flex-col gap-1 min-w-0"
    >
      <dt class="text-sm text-rui-text-secondary">
        {{ limit.label }}
      </dt>
      <dd class="m-0 text-base font-medium text-rui-text">
        {{ limit.value }}
      </dd>
    </div>
  </dl>
</template>
