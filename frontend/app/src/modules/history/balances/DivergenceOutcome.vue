<script setup lang="ts">
import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';

/**
 * A divergence search's result as a status, so it reads as an outcome rather than as more description.
 * Renders nothing when there is no text to show, as for a diverged result whose comparison table
 * carries its summary.
 */
const { status, summary, nextStep } = defineProps<{
  status: HistoricalBalanceDivergenceResponse['status'];
  summary?: string;
  nextStep?: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const type = computed<'success' | 'warning'>(() => (status === 'no_divergence' ? 'success' : 'warning'));

const title = computed<string>(() => {
  if (status === 'diverged')
    return t('balance_divergence.status.diverged');
  if (status === 'diverged_from_start')
    return t('balance_divergence.status.diverged_from_start');
  if (status === 'no_checkpoints')
    return t('balance_divergence.status.no_checkpoints');
  return t('balance_divergence.status.no_divergence');
});
</script>

<template>
  <RuiAlert
    v-if="summary || nextStep"
    :type="type"
    :title="title"
    data-testid="divergence-outcome"
  >
    <p
      v-if="summary"
      data-testid="divergence-outcome-summary"
    >
      {{ summary }}
    </p>
    <p
      v-if="nextStep"
      class="mt-1 first:mt-0"
      data-testid="divergence-outcome-next-step"
    >
      {{ nextStep }}
    </p>
  </RuiAlert>
</template>
