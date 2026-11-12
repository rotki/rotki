<script setup lang="ts">
import type { ContextColorsType } from '@rotki/ui-library';
import type { SpamAssessment } from './use-spam-assessments';
import type { SpamPrediction } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { useSpamSignal } from './use-spam-signal';

const { assessment } = defineProps<{
  /**
   * The model's state for this token; nothing is rendered without one. The component never infers
   * a score from the token itself.
   */
  assessment?: SpamAssessment;
}>();

const { t } = useI18n({ useScope: 'global' });

const describeSignal = useSpamSignal();

const prediction = computed<SpamPrediction | undefined>(() => (assessment?.status === 'ready' ? assessment.prediction : undefined));
const flagged = computed<boolean>(() => get(prediction)?.flagged ?? false);
const percentage = computed<number>(() => Math.round((get(prediction)?.spamProbability ?? 0) * 100));

const chip = computed<{ color: ContextColorsType; label: string } | undefined>(() => {
  switch (assessment?.status) {
    case 'ready':
      return get(flagged)
        ? { color: 'warning', label: t('spam_estimate.high') }
        : { color: 'secondary', label: t('spam_estimate.low') };
    case 'unavailable':
      return { color: 'error', label: t('spam_estimate.unavailable') };
    case 'unsupported':
      return { color: 'secondary', label: t('spam_estimate.unsupported') };
    case 'loading':
      return { color: 'secondary', label: t('spam_estimate.checking') };
    default:
      return undefined;
  }
});

const status = computed<{ title: string; hint: string } | undefined>(() => {
  switch (assessment?.status) {
    case 'unavailable':
      return { hint: t('spam_estimate.unavailable_reason'), title: t('spam_estimate.unavailable') };
    case 'unsupported':
      return { hint: t('spam_estimate.unsupported_hint'), title: t('spam_estimate.unsupported') };
    case 'loading':
      return { hint: t('spam_estimate.checking_hint'), title: t('spam_estimate.checking') };
    default:
      return undefined;
  }
});

const signals = computed<(ReturnType<typeof describeSignal> & { id: string })[]>(() => get(prediction)?.observedSignals.map(signal => ({
  ...describeSignal(signal),
  id: `${signal.field}:${signal.code}`,
})) ?? []);
</script>

<template>
  <RuiTooltip
    v-if="chip"
    :open-delay="200"
    :options="{ placement: 'top' }"
  >
    <template #activator>
      <RuiChip
        :color="chip.color"
        :class-names="{ content: 'text-caption-2!' }"
        class="font-bold leading-3 uppercase p-0.5! mb-0.5 mt-0.5"
        size="sm"
        variant="tonal"
      >
        <span data-testid="spam-state">{{ chip.label }}</span>
        <span
          v-if="prediction"
          class="ms-1"
          data-testid="spam-score"
        >
          {{ t('spam_estimate.score', { percentage }) }}
        </span>
      </RuiChip>
    </template>

    <div class="flex flex-col gap-3 max-w-80 text-wrap py-1">
      <template v-if="prediction">
        <div class="flex items-start gap-2">
          <RuiIcon
            :name="flagged ? 'lu-shield-alert' : 'lu-shield-question'"
            class="shrink-0 mt-0.5"
            size="20"
            aria-hidden="true"
          />
          <div class="flex flex-col gap-1">
            <div class="font-bold">
              {{ t('spam_estimate.heading', { percentage }) }}
            </div>
            <div>
              {{ flagged ? t('spam_estimate.high_hint') : t('spam_estimate.low_hint') }}
            </div>
          </div>
        </div>
        <div>
          <div class="font-medium mb-2">
            {{ t('spam_estimate.observed_signals') }}
          </div>
          <ul
            v-if="signals.length > 0"
            class="flex flex-col gap-2"
            data-testid="spam-signals"
          >
            <li
              v-for="signal in signals"
              :key="signal.id"
              class="flex items-start gap-2"
            >
              <RuiIcon
                :name="signal.icon"
                class="shrink-0 mt-0.5"
                size="16"
                aria-hidden="true"
              />
              <span>{{ signal.text }}</span>
            </li>
          </ul>
          <div
            v-else
            class="text-caption"
          >
            {{ t('spam_estimate.no_signals') }}
          </div>
        </div>
        <div
          class="border-t border-current/20 pt-2 text-caption"
          data-testid="spam-advisory"
        >
          {{ t('spam_estimate.advisory') }}
        </div>
      </template>

      <template v-else-if="status">
        <div class="font-bold">
          {{ status.title }}
        </div>
        <div>{{ status.hint }}</div>
      </template>
    </div>
  </RuiTooltip>
</template>
