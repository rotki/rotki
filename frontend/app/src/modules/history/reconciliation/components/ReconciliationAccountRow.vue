<script setup lang="ts">
import type { ReconciliationAccount } from '@/modules/history/reconciliation/schemas';
import { useLocations } from '@/modules/core/common/use-locations';
import { ACCOUNT_SUMMARY_LABEL } from '@/modules/history/reconciliation/messages';
import { type AccountSummary, accountSummaryFor, type ReconciliationView } from '@/modules/history/reconciliation/use-reconciliation-rows';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { account, view, isOpen, loading = false, error, colspan } = defineProps<{
  account: ReconciliationAccount;
  view: ReconciliationView;
  isOpen: boolean;
  loading?: boolean;
  error?: string;
  colspan: number;
}>();

const emit = defineEmits<{
  retry: [];
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { useLocationData } = useLocations();

const locationName = computed<string>(() => get(useLocationData(() => account.location))?.name ?? account.location);
const needsAttention = computed<boolean>(() => account.counts.mismatch + account.counts.blocked > 0);
const summary = computed<AccountSummary>(() => accountSummaryFor(account, view));

/**
 * The account's one-line counts, oldest idea first: what needs work, then what matches and what
 * cannot be checked. Zero groups are omitted, so a clean account says only that it matches.
 */
const summaryParts = computed<string[]>(() => {
  const { blocked, hidden, mismatch, notChecked, reconciled } = get(summary);
  const counts: { count: number; key: keyof typeof ACCOUNT_SUMMARY_LABEL }[] = view === 'attention'
    ? [
        { count: mismatch, key: 'mismatch' },
        { count: blocked, key: 'blocked' },
        { count: hidden, key: 'hidden' },
      ]
    : [
        { count: mismatch, key: 'mismatch' },
        { count: blocked, key: 'blocked' },
        { count: reconciled, key: 'reconciled' },
        { count: notChecked, key: 'not_checked' },
      ];

  return counts
    .filter(({ count }) => count > 0)
    .map(({ count, key }) => t(ACCOUNT_SUMMARY_LABEL[key], { count }, count));
});
</script>

<template>
  <td
    :colspan="colspan"
    class="py-2 px-2"
    data-testid="reconciliation-account-row"
  >
    <div class="flex flex-wrap items-center gap-2">
      <RuiButton
        icon
        variant="text"
        size="sm"
        :aria-expanded="isOpen"
        data-testid="reconciliation-account-toggle"
        @click="emit('toggle')"
      >
        <RuiIcon :name="isOpen ? 'lu-chevron-down' : 'lu-chevron-right'" />
      </RuiButton>
      <span
        v-if="needsAttention"
        class="size-2 rounded-full bg-rui-error shrink-0"
        data-testid="reconciliation-account-attention"
      />
      <span class="font-medium">{{ locationName }}</span>
      <HashLink
        v-if="account.locationLabel"
        :text="account.locationLabel"
        :location="account.location"
        reveal-actions
      />
      <span
        v-else
        class="text-rui-text-secondary text-sm"
      >
        {{ t('data_issues.reconciliation.no_account_label') }}
      </span>
    </div>

    <div class="flex flex-wrap items-center gap-2 pl-10 text-sm text-rui-text-secondary">
      <template v-if="loading">
        <RuiIcon
          name="lu-loader-circle"
          size="14"
          class="animate-spin"
        />
        <span>{{ t('data_issues.reconciliation.loading_balances') }}</span>
      </template>
      <template v-else-if="error">
        <span class="text-rui-error">{{ error }}</span>
        <RuiButton
          size="sm"
          variant="text"
          color="primary"
          data-testid="reconciliation-account-retry"
          @click="emit('retry')"
        >
          {{ t('common.actions.retry') }}
        </RuiButton>
      </template>
      <span
        v-else
        data-testid="reconciliation-account-summary"
      >
        {{ summaryParts.join(' · ') }}
      </span>
    </div>
  </td>
</template>
