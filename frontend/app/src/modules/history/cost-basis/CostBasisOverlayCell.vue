<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { get } from '@vueuse/shared';
import { computed, onWatcherCleanup, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import {
  COST_BASIS_FIAT_FORMAT,
  type CostBasisSummary,
  CostBasisSummaryKind,
  mergeCostBasisSummaries,
  summarizeCostBasis,
} from '@/modules/history/cost-basis/cost-basis-helpers';
import CostBasisReceiveDetails from '@/modules/history/cost-basis/CostBasisReceiveDetails.vue';
import CostBasisSpendDetails from '@/modules/history/cost-basis/CostBasisSpendDetails.vue';
import { CostBasisDirection, type CostBasisEntry } from '@/modules/history/cost-basis/types';
import { CostBasisStatus } from '@/modules/history/cost-basis/use-cost-basis-overlay';
import { injectCostBasisOverlay } from '@/modules/history/cost-basis/use-cost-basis-overlay-context';

const { event, fallbackEvent, siblingEvents = [] } = defineProps<{
  event: HistoryEventEntry;
  /**
   * Shown instead of `event` when `event` changes no cost basis, as for the fiat side of a
   * purchase, whose received asset is what carries the cost.
   */
  fallbackEvent?: HistoryEventEntry;
  /** Further events added up with `event` on the row, as the other spends of a multi-asset swap. */
  siblingEvents?: HistoryEventEntry[];
}>();

interface ShownEntry {
  entry: CostBasisEntry;
  /** The amount of the event the entry belongs to. */
  amount: HistoryEventEntry['amount'];
}

/** The status of a row of several events: the least settled one wins. */
const STATUS_PRECEDENCE: CostBasisStatus[] = [
  CostBasisStatus.ERROR,
  CostBasisStatus.LOADING,
  CostBasisStatus.PROCESSING,
  CostBasisStatus.READY,
];

const { t } = useI18n({ useScope: 'global' });
const context = injectCostBasisOverlay();

const enabled = computed<boolean>(() => !!context && get(context.enabled));

const primaryEvents = computed<HistoryEventEntry[]>(() => [event, ...siblingEvents]);

/** The identifiers this cell needs, joined so a new array with the same events changes nothing. */
const registeredKey = computed<string>(() => [...get(primaryEvents), ...(fallbackEvent ? [fallbackEvent] : [])]
  .map(({ identifier }) => identifier)
  .join(','));

const shownEvents = computed<HistoryEventEntry[]>(() => {
  const events = get(primaryEvents);
  if (fallbackEvent && context && events.every(({ identifier }) => context.overlay.statusFor(identifier) === CostBasisStatus.EMPTY))
    return [fallbackEvent];
  return events;
});

const status = computed<CostBasisStatus | undefined>(() => {
  if (!context)
    return undefined;
  const statuses = new Set(get(shownEvents).map(({ identifier }) => context.overlay.statusFor(identifier)));
  return STATUS_PRECEDENCE.find(candidate => statuses.has(candidate)) ?? CostBasisStatus.EMPTY;
});

const entries = computed<ShownEntry[]>(() => get(shownEvents).flatMap(({ amount, identifier }) =>
  (context?.overlay.entriesFor(identifier) ?? []).map(entry => ({ amount, entry }))));

const summary = computed<CostBasisSummary | undefined>(() => mergeCostBasisSummaries(get(shownEvents)
  .map(({ amount, identifier }) => summarizeCostBasis(context?.overlay.entriesFor(identifier) ?? [], amount))
  .filter((summary): summary is CostBasisSummary => summary !== undefined)));

/** What the figure under a row's main one is, since a cost, a basis and a moved basis differ. */
const basisLabel = computed<string>(() => {
  switch (get(summary)?.kind) {
    case CostBasisSummaryKind.ACQUISITION:
      return t('cost_basis_overlay.labels.acquisition');
    case CostBasisSummaryKind.TRANSFER:
      return t('cost_basis_overlay.labels.transfer');
    default:
      return t('cost_basis_overlay.labels.disposal');
  }
});

watch([enabled, registeredKey], ([isEnabled, key]) => {
  if (!context || !isEnabled)
    return;
  for (const identifier of new Set(key.split(',').map(Number)))
    onWatcherCleanup(context.overlay.registerEvent(identifier));
}, { immediate: true });
</script>

<template>
  <div
    v-if="enabled"
    class="w-32 xl:w-40 shrink-0 flex items-center justify-end text-sm"
    data-testid="cost-basis-overlay-cell"
  >
    <RuiSkeletonLoader
      v-if="status === CostBasisStatus.LOADING"
      class="w-20 h-4"
    />

    <RuiTooltip
      v-else-if="status === CostBasisStatus.ERROR"
      :open-delay="200"
    >
      <template #activator>
        <RuiIcon
          name="lu-circle-alert"
          class="text-rui-error"
          size="16"
          data-testid="cost-basis-error"
        />
      </template>
      {{ t('cost_basis_overlay.error') }}
    </RuiTooltip>

    <RuiTooltip
      v-else-if="status === CostBasisStatus.PROCESSING"
      :open-delay="200"
    >
      <template #activator>
        <span
          class="flex items-center gap-1.5 text-rui-text-secondary"
          data-testid="cost-basis-pending"
        >
          <RuiIcon
            name="lu-clock-alert"
            size="14"
            class="text-rui-warning"
          />
          {{ t('cost_basis_overlay.processing') }}
        </span>
      </template>
      {{ t('cost_basis_overlay.stale') }}
    </RuiTooltip>

    <div
      v-else-if="!summary"
      class="flex items-center justify-end gap-1.5"
      data-testid="cost-basis-empty"
    >
      <span class="text-rui-text-disabled">{{ t('accounting_overlay.no_data') }}</span>
      <RuiTooltip
        :open-delay="300"
        :options="{ placement: 'left' }"
      >
        <template #activator>
          <RuiIcon
            name="lu-info"
            size="14"
            class="text-rui-text-secondary cursor-help shrink-0 m-0.5"
          />
        </template>
        {{ t('cost_basis_overlay.no_data') }}
      </RuiTooltip>
    </div>

    <div
      v-else
      class="flex items-center justify-end gap-1.5"
    >
      <div class="flex flex-col items-end leading-tight">
        <span
          v-if="summary.pnl"
          class="flex items-center gap-1"
        >
          <RuiTooltip
            v-if="summary.taxfreePnl"
            :open-delay="200"
            :options="{ placement: 'left' }"
          >
            <template #activator>
              <button
                type="button"
                class="flex rounded-sm text-rui-success focus-visible:outline focus-visible:outline-rui-primary"
                :aria-label="t('cost_basis_overlay.taxfree_gain')"
                data-testid="cost-basis-taxfree"
              >
                <RuiIcon
                  name="lu-leaf"
                  size="12"
                />
              </button>
            </template>
            <i18n-t
              keypath="cost_basis_overlay.taxfree_hint"
              tag="span"
              scope="global"
            >
              <template #amount>
                <FiatDisplay
                  :value="summary.taxfreePnl"
                  :format="COST_BASIS_FIAT_FORMAT"
                  class="inline"
                />
              </template>
            </i18n-t>
          </RuiTooltip>
          <FiatDisplay
            :value="summary.pnl"
            :format="COST_BASIS_FIAT_FORMAT"
            pnl
            class="font-medium"
            data-testid="cost-basis-pnl"
          />
        </span>
        <span
          class="flex items-center gap-1"
          :class="summary.pnl ? 'text-xs text-rui-text-secondary' : 'font-medium'"
          data-testid="cost-basis-basis"
        >
          <span class="text-xs text-rui-text-secondary">{{ basisLabel }}</span>
          <FiatDisplay
            :value="summary.basis"
            :format="COST_BASIS_FIAT_FORMAT"
          />
        </span>
      </div>
      <RuiMenu
        class="flex"
        open-on-hover
        lazy
        :close-delay="200"
        :close-on-content-click="false"
        :options="{ placement: 'left', strategy: 'fixed', autoUpdate: { resize: false, scroll: false } }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="p-0.5! shrink-0"
            :aria-label="t('cost_basis_overlay.show_details')"
            v-bind="attrs"
          >
            <RuiIcon
              name="lu-info"
              size="14"
              class="text-rui-text-secondary"
            />
          </RuiButton>
        </template>
        <div class="w-80 py-1">
          <template
            v-for="({ entry, amount }, index) in entries"
            :key="index"
          >
            <CostBasisSpendDetails
              v-if="entry.direction === CostBasisDirection.SPEND"
              :entry="entry"
              :amount="amount"
              class="px-4 py-3"
              :class="{ 'border-t border-default': index > 0 }"
            />
            <CostBasisReceiveDetails
              v-else
              :entry="entry"
              :amount="amount"
              class="px-4 py-3"
              :class="{ 'border-t border-default': index > 0 }"
            />
          </template>
        </div>
      </RuiMenu>
    </div>
  </div>
</template>
