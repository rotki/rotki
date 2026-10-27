<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import { sharedDecimals } from '@/modules/assets/amount-display/amount-comparison';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AmountDiffDisplay from '@/modules/assets/amount-display/components/AmountDiffDisplay.vue';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import DivergenceSearchWindow from '@/modules/history/balances/DivergenceSearchWindow.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { boundaries, asset } = defineProps<{
  boundaries: DivergenceBoundaryEvent[];
  asset?: string;
  location?: string;
}>();

const emit = defineEmits<{
  view: [boundary: DivergenceBoundaryEvent];
}>();

defineSlots<{
  footer?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
const { useAssetField } = useAssetInfoRetrieval();

/** The table's amounts carry no symbol of their own, so the unit is stated once in its corner. */
const unit = useAssetField(() => asset, 'symbol', { collectionParent: false });

const matching = computed<DivergenceBoundaryEvent | undefined>(() => boundaries.find(boundary => boundary.key === 'last_matching'));
const diverged = computed<DivergenceBoundaryEvent | undefined>(() => boundaries.find(boundary => boundary.key === 'first_diverged'));

/** With both events there is a window to search, and it carries their block numbers. */
const hasWindow = computed<boolean>(() => !!get(matching) && !!get(diverged));

const gridColumns = computed<string>(() => `auto repeat(${boundaries.length}, minmax(0, 1fr))`);
const fullRow = { gridColumn: '1 / -1' };

/** One precision for every amount, so the columns line up and no value is rounded away. */
const decimals = computed<number>(() => sharedDecimals(...boundaries.flatMap(({ event }) => [
  event.trackedBalance,
  event.onchainBalance,
  event.difference,
])));

/** `difference` is on-chain minus tracked, so a negative one means rotki tracks more than the chain holds. */
const direction = computed<string | undefined>(() => {
  const difference = get(diverged)?.event.difference;
  if (!difference || difference.isZero())
    return undefined;
  return difference.isNegative()
    ? t('balance_divergence.tracked_higher')
    : t('balance_divergence.tracked_lower');
});

function isMatching(boundary: DivergenceBoundaryEvent): boolean {
  return boundary.color === 'success';
}

/** An exact zero keeps the user's own precision, since padding it to the table's precision is only noise. */
function decimalsFor(...amounts: BigNumber[]): number | undefined {
  return amounts.every(amount => amount.isZero()) ? undefined : get(decimals);
}
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded-sm border border-default p-3 text-sm"
    data-testid="divergence-comparison"
  >
    <p
      v-if="direction"
      class="inline-flex items-center gap-1.5 text-rui-text-secondary"
      data-testid="divergence-headline"
    >
      <RuiIcon
        name="lu-triangle-alert"
        size="14"
        class="text-rui-warning"
      />
      {{ direction }}
    </p>

    <div
      class="grid items-center gap-x-4 gap-y-2"
      :style="{ gridTemplateColumns: gridColumns }"
    >
      <span
        class="max-w-20 self-end truncate text-xs text-rui-text-secondary"
        :title="unit"
        data-testid="divergence-unit"
      >
        {{ unit }}
      </span>
      <span
        v-for="boundary in boundaries"
        :key="boundary.key"
        class="flex justify-end"
        data-testid="divergence-boundary"
        :data-key="boundary.key"
      >
        <RuiButton
          variant="text"
          size="sm"
          :color="isMatching(boundary) ? 'success' : 'warning'"
          class="-mx-1.5 -my-1 font-medium"
          :disabled="!boundary.event.groupIdentifier"
          :title="t('balance_divergence.view_event')"
          data-testid="view-divergence"
          :data-key="boundary.key"
          @click="emit('view', boundary)"
        >
          <template #prepend>
            <RuiIcon
              :name="isMatching(boundary) ? 'lu-check' : 'lu-triangle-alert'"
              size="16"
            />
          </template>
          {{ isMatching(boundary) ? t('balance_divergence.last_matching') : t('balance_divergence.first_diverged') }}
        </RuiButton>
      </span>

      <span class="text-rui-text-secondary">{{ t('common.datetime') }}</span>
      <div
        v-for="boundary in boundaries"
        :key="boundary.key"
        class="flex flex-col items-end"
      >
        <DateDisplay
          class="text-right"
          :timestamp="boundary.event.timestamp"
          data-testid="divergence-date"
          :data-key="boundary.key"
        />
        <span
          v-if="!hasWindow"
          class="text-xs text-rui-text-secondary"
          data-testid="divergence-block"
          :data-key="boundary.key"
        >
          {{ t('balance_divergence.block') }} {{ boundary.event.blockNumber }}
        </span>
      </div>

      <template v-if="hasWindow && matching && diverged">
        <span />
        <DivergenceSearchWindow
          :style="{ gridColumn: `span ${boundaries.length}` }"
          :from="matching.event"
          :to="diverged.event"
        />
      </template>

      <span class="text-rui-text-secondary">{{ t('balance_divergence.tracked') }}</span>
      <AmountDiffDisplay
        v-for="boundary in boundaries"
        :key="boundary.key"
        class="justify-self-end"
        :amount="boundary.event.trackedBalance"
        :reference="boundary.event.onchainBalance"
        :decimals="decimalsFor(boundary.event.trackedBalance, boundary.event.onchainBalance)"
      />

      <span class="text-rui-text-secondary">{{ t('balance_divergence.onchain') }}</span>
      <AmountDiffDisplay
        v-for="boundary in boundaries"
        :key="boundary.key"
        class="justify-self-end"
        :amount="boundary.event.onchainBalance"
        :reference="boundary.event.trackedBalance"
        :decimals="decimalsFor(boundary.event.trackedBalance, boundary.event.onchainBalance)"
      />

      <div
        class="border-t border-default"
        :style="fullRow"
      />

      <span class="font-medium">{{ t('balance_divergence.difference') }}</span>
      <div
        v-for="boundary in boundaries"
        :key="boundary.key"
        class="flex justify-end"
      >
        <span
          v-if="boundary.event.difference.isZero()"
          class="inline-flex items-center gap-1 rounded-sm bg-rui-success/10 px-2 py-0.5 font-medium text-rui-success"
          data-testid="divergence-match"
          :data-key="boundary.key"
        >
          <RuiIcon
            name="lu-check"
            size="14"
          />
          {{ t('balance_divergence.match') }}
        </span>
        <AssetAmountDisplay
          v-else
          class="rounded-sm px-2 py-0.5 font-medium"
          :class="isMatching(boundary) ? 'bg-rui-success/10 text-rui-success' : 'bg-rui-warning/10 text-rui-warning'"
          :amount="boundary.event.difference"
          :decimals="decimalsFor(boundary.event.difference)"
          data-testid="divergence-difference"
          :data-key="boundary.key"
        />
      </div>
    </div>

    <div
      class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-rui-text-secondary"
      data-testid="divergence-footer"
    >
      <slot name="footer" />
      <span
        v-for="boundary in boundaries"
        :key="boundary.key"
        class="inline-flex items-center gap-1"
        data-testid="divergence-tx"
        :data-key="boundary.key"
      >
        <RuiIcon
          :name="isMatching(boundary) ? 'lu-check' : 'lu-triangle-alert'"
          size="12"
          :class="isMatching(boundary) ? 'text-rui-success' : 'text-rui-warning'"
        />
        {{ t('balance_divergence.event') }}
        <HashLink
          v-if="boundary.event.txHash"
          :text="boundary.event.txHash"
          type="transaction"
          :location="location"
          :truncate-length="4"
        />
        <template v-else>
          {{ t('balance_divergence.missing_group') }}
        </template>
      </span>
    </div>
  </div>
</template>
