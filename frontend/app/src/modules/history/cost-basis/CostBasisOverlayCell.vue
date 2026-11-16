<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { type CostBasisSummary, CostBasisSummaryKind, summarizeCostBasis } from '@/modules/history/cost-basis/cost-basis-helpers';
import CostBasisReceiveDetails from '@/modules/history/cost-basis/CostBasisReceiveDetails.vue';
import CostBasisSpendDetails from '@/modules/history/cost-basis/CostBasisSpendDetails.vue';
import { CostBasisDirection, type CostBasisEntry } from '@/modules/history/cost-basis/types';
import { CostBasisStatus } from '@/modules/history/cost-basis/use-cost-basis-overlay';
import { injectCostBasisOverlay } from '@/modules/history/cost-basis/use-cost-basis-overlay-context';

const { event } = defineProps<{ event: HistoryEventEntry }>();

const { t } = useI18n({ useScope: 'global' });
const context = injectCostBasisOverlay();

const enabled = computed<boolean>(() => !!context && get(context.enabled));
const stale = computed<boolean>(() => !!context && get(context.overlay.stale));
const status = computed<CostBasisStatus | undefined>(() => context?.overlay.statusFor(event.identifier));
const entries = computed<CostBasisEntry[]>(() => context?.overlay.entriesFor(event.identifier) ?? []);
const summary = computed<CostBasisSummary | undefined>(() => summarizeCostBasis(get(entries), event.amount));

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

watch([enabled, () => event.identifier], ([isEnabled, identifier]) => {
  if (context && isEnabled)
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
      v-else-if="!summary && stale"
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
      <RuiTooltip
        v-if="stale"
        :open-delay="200"
      >
        <template #activator>
          <RuiIcon
            name="lu-clock-alert"
            class="text-rui-warning"
            size="14"
            data-testid="cost-basis-stale"
          />
        </template>
        {{ t('cost_basis_overlay.stale') }}
      </RuiTooltip>
      <div class="flex flex-col items-end leading-tight">
        <FiatDisplay
          v-if="summary.pnl"
          :value="summary.pnl"
          pnl
          class="font-medium"
          data-testid="cost-basis-pnl"
        />
        <span
          class="flex items-center gap-1"
          :class="summary.pnl ? 'text-xs text-rui-text-secondary' : 'font-medium'"
          data-testid="cost-basis-basis"
        >
          <span class="text-xs text-rui-text-secondary">{{ basisLabel }}</span>
          <FiatDisplay :value="summary.basis" />
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
        <div class="p-4 flex flex-col gap-4">
          <template
            v-for="(entry, index) in entries"
            :key="index"
          >
            <RuiDivider v-if="index > 0" />
            <CostBasisSpendDetails
              v-if="entry.direction === CostBasisDirection.SPEND"
              :entry="entry"
            />
            <CostBasisReceiveDetails
              v-else
              :entry="entry"
            />
          </template>
        </div>
      </RuiMenu>
    </div>
  </div>
</template>
