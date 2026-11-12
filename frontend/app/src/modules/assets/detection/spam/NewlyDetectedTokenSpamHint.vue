<script setup lang="ts">
import type { SpamPrediction } from '@/modules/assets/api/use-asset-spam-prediction-api';
import { useSpamSignal } from './use-spam-signal';

const {
  prediction: predictionProp,
  unavailable = false,
} = defineProps<{
  /**
   * The model output for this token.
   *
   * `null` means the backend could not assess the asset. `undefined` means the estimate is still
   * being fetched. The component never infers a score from the token itself.
   */
  prediction?: SpamPrediction | null;
  /** The request for this token failed; the token row itself is still local and intact. */
  unavailable?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const prediction = computed<SpamPrediction | undefined>(() => get(predictionProp) ?? undefined);
const isUnsupported = computed<boolean>(() => get(predictionProp) === null);
const isPending = computed<boolean>(() => get(predictionProp) === undefined && !get(unavailable));

const percentage = computed<number>(() => Math.round((get(prediction)?.spamProbability ?? 0) * 100));
const describeSignal = useSpamSignal();
const signals = computed<(ReturnType<typeof describeSignal> & { id: string })[]>(() => get(prediction)?.observedSignals.map(signal => ({
  ...describeSignal(signal),
  id: signal,
})) ?? []);
const high = computed<boolean>(() => {
  const value = get(prediction);
  return value !== undefined && value.spamProbability >= value.threshold;
});
</script>

<template>
  <RuiTooltip
    :open-delay="200"
    :options="{ placement: 'top' }"
  >
    <template #activator>
      <RuiChip
        v-if="prediction"
        :color="high ? 'warning' : 'secondary'"
        :class-names="{ content: 'text-caption-2!' }"
        class="font-bold leading-3 uppercase p-0.5! mb-0.5 mt-0.5"
        size="sm"
        variant="tonal"
      >
        <span data-testid="spam-state">{{ high ? t('asset_table.newly_detected.spam.high') : t('asset_table.newly_detected.spam.low') }}</span>
        <span
          class="ms-1"
          data-testid="spam-score"
        >
          {{ t('asset_table.newly_detected.spam.score', { percentage }) }}
        </span>
      </RuiChip>
      <RuiChip
        v-else-if="unavailable"
        :class-names="{ content: 'text-caption-2!' }"
        class="font-bold leading-3 uppercase p-0.5! mb-0.5 mt-0.5"
        color="error"
        size="sm"
        variant="tonal"
      >
        <span data-testid="spam-state">{{ t('asset_table.newly_detected.spam.unavailable') }}</span>
      </RuiChip>
      <RuiChip
        v-else-if="isUnsupported"
        :class-names="{ content: 'text-caption-2!' }"
        class="font-bold leading-3 uppercase p-0.5! mb-0.5 mt-0.5"
        color="secondary"
        size="sm"
        variant="tonal"
      >
        <span data-testid="spam-state">{{ t('asset_table.newly_detected.spam.unsupported') }}</span>
      </RuiChip>
      <RuiChip
        v-else-if="isPending"
        :class-names="{ content: 'text-caption-2!' }"
        class="font-bold leading-3 uppercase p-0.5! mb-0.5 mt-0.5"
        color="secondary"
        size="sm"
        variant="tonal"
      >
        <span data-testid="spam-state">{{ t('asset_table.newly_detected.spam.checking') }}</span>
      </RuiChip>
    </template>

    <div class="flex flex-col gap-3 max-w-80 text-wrap py-1">
      <template v-if="prediction">
        <div class="flex items-start gap-2">
          <RuiIcon
            :name="high ? 'lu-shield-alert' : 'lu-shield-question'"
            class="shrink-0 mt-0.5"
            size="20"
            aria-hidden="true"
          />
          <div class="flex flex-col gap-1">
            <div class="font-bold">
              {{ t('asset_table.newly_detected.spam.heading', { percentage }) }}
            </div>
            <div>
              {{ high ? t('asset_table.newly_detected.spam.high_hint') : t('asset_table.newly_detected.spam.low_hint') }}
            </div>
          </div>
        </div>
        <div>
          <div class="font-medium mb-2">
            {{ t('asset_table.newly_detected.spam.observed_signals') }}
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
            {{ t('asset_table.newly_detected.spam.no_signals') }}
          </div>
        </div>
        <div
          class="border-t border-current/20 pt-2 text-caption"
          data-testid="spam-advisory"
        >
          {{ t('asset_table.newly_detected.spam.advisory') }}
        </div>
      </template>

      <template v-else-if="unavailable">
        <div class="font-bold">
          {{ t('asset_table.newly_detected.spam.unavailable') }}
        </div>
        <div>{{ t('asset_table.newly_detected.spam.unavailable_reason') }}</div>
      </template>

      <template v-else-if="isUnsupported">
        <div class="font-bold">
          {{ t('asset_table.newly_detected.spam.unsupported') }}
        </div>
        <div>{{ t('asset_table.newly_detected.spam.unsupported_hint') }}</div>
      </template>

      <template v-else>
        <div class="font-bold">
          {{ t('asset_table.newly_detected.spam.checking') }}
        </div>
        <div>{{ t('asset_table.newly_detected.spam.checking_hint') }}</div>
      </template>
    </div>
  </RuiTooltip>
</template>
