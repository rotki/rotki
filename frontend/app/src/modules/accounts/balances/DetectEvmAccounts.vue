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

/** A count wide enough to reserve room for any realistic number of chains. */
const WIDEST_COUNT = 99;

const label = computed<string>(() => get(outcome) ?? t('blockchain_balances.evm_detection.title'));

/**
 * Invisible copies of every label the button can carry, sharing one grid cell with the visible
 * label, so the button always has the width of the longest and a run never shifts the toolbar.
 */
const sizers = computed<string[]>(() => [
  t('blockchain_balances.evm_detection.title'),
  t('blockchain_balances.evm_detection.none'),
  t('blockchain_balances.evm_detection.found', { count: WIDEST_COUNT }, WIDEST_COUNT),
]);

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
  <RuiTooltip
    :options="{ placement: 'right' }"
    :open-delay="400"
    :class-names="{ tooltip: 'max-w-[16rem]' }"
  >
    <template #activator>
      <RuiButton
        color="primary"
        size="xl"
        :loading="isEvmAccountsDetecting"
        :disabled="isEvmAccountsDetecting"
        data-testid="detect-evm-accounts"
        @click="detectEvmAccounts()"
      >
        <template #prepend>
          <RuiIcon :name="outcome ? 'lu-check' : 'lu-radar'" />
        </template>
        <span class="grid">
          <span
            v-for="sizer in sizers"
            :key="sizer"
            class="[grid-area:1/1] invisible"
            aria-hidden="true"
          >
            {{ sizer }}
          </span>
          <span
            class="[grid-area:1/1] text-center"
            aria-live="polite"
            data-testid="detect-evm-accounts-label"
          >
            {{ label }}
          </span>
        </span>
      </RuiButton>
    </template>
    {{ t('blockchain_balances.evm_detection.tooltip') }}
  </RuiTooltip>
</template>
