<script setup lang="ts">
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { useEvmAccountDetection } from '@/modules/accounts/use-evm-account-detection';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** How long the button shows the outcome of a run before its label returns, in milliseconds. */
const OUTCOME_DURATION = 4000;

const { t } = useI18n({ useScope: 'global' });

const outcome = ref<string>();

const { lastRun } = storeToRefs(useDetectedAccountsStore());

const { useIsActive } = useTaskCenter();
const isEvmAccountsDetecting = useIsActive(ActivityKind.ACCOUNTS, ActivityPart.DETECT);
const { detectEvmAccounts } = useEvmAccountDetection();

const { start: clearOutcomeLater, stop: keepOutcome } = useTimeoutFn(() => set(outcome, undefined), OUTCOME_DURATION, { immediate: false });

const label = computed<string>(() => get(outcome) ?? t('blockchain_balances.evm_detection.title'));

/**
 * Counts chains, not (chain, address) pairs: a user thinks of one address added on five chains.
 * The chains themselves are named on the row chip, so the button only says how many.
 */
function describe(found: { chain: string }[]): string {
  const chains = found.map(account => account.chain).filter(uniqueStrings).length;
  return chains > 0
    ? t('blockchain_balances.evm_detection.found', { count: chains }, chains)
    : t('blockchain_balances.evm_detection.none');
}

/** A new run clears the last outcome at once, so a running button never shows the previous result. */
watch(lastRun, (found) => {
  if (found === undefined) {
    keepOutcome();
    set(outcome, undefined);
    return;
  }

  set(outcome, describe(found));
  clearOutcomeLater();
});
</script>

<template>
  <!-- an entry of the Refresh menu: the label turns into the run's outcome, the line below explains it -->
  <RuiButton
    variant="list"
    :disabled="isEvmAccountsDetecting"
    data-testid="detect-evm-accounts"
    @click="detectEvmAccounts()"
  >
    <template #prepend>
      <RuiProgress
        v-if="isEvmAccountsDetecting"
        variant="indeterminate"
        circular
        size="18"
        thickness="2"
      />
      <RuiIcon
        v-else
        size="18"
        :name="outcome ? 'lu-check' : 'lu-radar'"
      />
    </template>
    <span class="flex flex-col items-start text-left">
      <span
        aria-live="polite"
        data-testid="detect-evm-accounts-label"
      >
        {{ label }}
      </span>
      <span class="text-caption font-normal text-rui-text-secondary whitespace-normal">
        {{ t('blockchain_balances.evm_detection.description') }}
      </span>
    </span>
  </RuiButton>
</template>
