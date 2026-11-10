<script setup lang="ts">
import type { ReconciliationAccount } from '@/modules/history/reconciliation/schemas';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { ACCOUNT_SUMMARY_LABEL } from '@/modules/history/reconciliation/messages';
import { type AccountSummary, accountSummaryFor, type ReconciliationView } from '@/modules/history/reconciliation/use-reconciliation-rows';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { account, view, isOpen, loading = false, error, colspan } = defineProps<{
  account: ReconciliationAccount;
  view: ReconciliationView;
  isOpen: boolean;
  loading?: boolean;
  /** What the account's last fetch threw; the strip words it and decides on a retry. */
  error?: unknown;
  colspan: number;
}>();

const emit = defineEmits<{
  retry: [];
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { useLocationData } = useLocations();

const { matchChain } = useSupportedChains();
const locationData = useLocationData(() => account.location);

/** Only a blockchain account's label is an address; an exchange or import label is a plain name. */
const isChainAccount = computed<boolean>(() => matchChain(account.location) !== undefined);

const locationName = computed<string>(() => get(locationData)?.name ?? account.location);
const summary = computed<AccountSummary>(() => accountSummaryFor(account, view));

/** Red for a mismatch, amber for stopped processing only, matching the headline and the bar. */
const attentionDotClass = computed<string | undefined>(() => {
  if (account.counts.mismatch > 0)
    return 'bg-rui-error';
  return account.counts.blocked > 0 ? 'bg-rui-warning' : undefined;
});

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
    class="py-1.5 px-2 bg-white dark:bg-rui-grey-900"
    data-testid="reconciliation-account-row"
  >
    <div class="flex items-start gap-2">
      <RuiButton
        icon
        variant="text"
        size="sm"
        class="shrink-0"
        :aria-expanded="isOpen"
        data-testid="reconciliation-account-toggle"
        @click="emit('toggle')"
      >
        <RuiIcon :name="isOpen ? 'lu-chevron-down' : 'lu-chevron-right'" />
      </RuiButton>
      <span class="flex w-2 h-7 shrink-0 items-center">
        <span
          v-if="attentionDotClass"
          class="size-2 rounded-full"
          :class="attentionDotClass"
          data-testid="reconciliation-account-attention"
        />
      </span>
      <div class="flex flex-col min-w-0 grow">
        <div class="flex flex-wrap items-center gap-x-2 min-h-7 text-sm">
          <span class="font-semibold text-rui-text">{{ locationName }}</span>
          <HashLink
            v-if="account.locationLabel && isChainAccount"
            :text="account.locationLabel"
            :location="account.location"
            reveal-actions
          />
          <span
            v-else-if="account.locationLabel"
            class="text-rui-text-secondary"
            data-testid="reconciliation-account-label"
          >
            {{ account.locationLabel }}
          </span>
          <span
            v-else
            class="text-rui-text-secondary"
          >
            {{ t('data_issues.reconciliation.no_account_label') }}
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-xs leading-5 text-rui-text-secondary">
          <template v-if="loading">
            <RuiIcon
              name="lu-loader-circle"
              size="14"
              class="animate-spin"
            />
            <span>{{ t('data_issues.reconciliation.loading_balances') }}</span>
          </template>
          <FailureStrip
            v-else-if="error !== undefined"
            class="grow"
            :title="t('data_issues.reconciliation.failure.account')"
            :failure="error"
            data-testid="reconciliation-account-failure"
            @retry="emit('retry')"
          />
          <span
            v-else
            data-testid="reconciliation-account-summary"
          >
            {{ summaryParts.join(' · ') }}
          </span>
        </div>
      </div>
    </div>
  </td>
</template>
