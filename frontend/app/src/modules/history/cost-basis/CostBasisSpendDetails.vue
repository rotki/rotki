<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { type BigNumber, Zero } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import { COST_BASIS_FIAT_FORMAT } from '@/modules/history/cost-basis/cost-basis-helpers';
import CostBasisBucketLabel from '@/modules/history/cost-basis/CostBasisBucketLabel.vue';
import { AVERAGE_COST_BASIS_METHOD, type CostBasisLot, type CostBasisSpend } from '@/modules/history/cost-basis/types';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

interface FigureRow {
  key: string;
  label: string;
  value: BigNumber;
}

const { entry, amount } = defineProps<{
  entry: CostBasisSpend;
  amount?: BigNumber;
}>();

const { t } = useI18n({ useScope: 'global' });

const isAverage = computed<boolean>(() => entry.method === AVERAGE_COST_BASIS_METHOD);

/**
 * The cost of each unit spent.
 *
 * @remarks
 * A spend from a single lot or under the average cost basis method has one unit basis on its
 * lots. When several lots with different bases are consumed, or part of the spend has no lot,
 * the unit basis is the total cost value divided by the amount spent.
 */
const basisPerUnit = computed<BigNumber>(() => {
  const lotsAmount = entry.lots.reduce((sum, lot) => sum.plus(lot.amount), Zero);
  const totalAmount = amount ?? lotsAmount;
  if (totalAmount.isZero())
    return Zero;
  if (entry.lots.length > 0 && lotsAmount.eq(totalAmount) && (entry.lots.length === 1 || get(isAverage)))
    return entry.lots[0].basisPerUnit;
  return entry.basisRemoved.dividedBy(totalAmount);
});

/**
 * The gains of the spend, under the figures they come from.
 *
 * @remarks
 * A move between two own accounts or an unpriced spend has no proceeds or realized gain, so it
 * has none. A tax free gain of zero is omitted.
 */
const gains = computed<FigureRow[]>(() => {
  const rows: FigureRow[] = [];
  if (entry.proceeds !== null && entry.realizedPnl !== null)
    rows.push({ key: 'gain', label: t('cost_basis_overlay.gain'), value: entry.realizedPnl });
  if (entry.taxfreePnl !== null && !entry.taxfreePnl.isZero())
    rows.push({ key: 'taxfree-gain', label: t('cost_basis_overlay.taxfree_gain'), value: entry.taxfreePnl });
  return rows;
});

/**
 * Each lot with the link to the event that acquired it, which keeps this overlay on at the
 * destination. A lot whose acquiring event is gone has no link.
 */
const lots = computed<{ lot: CostBasisLot; route?: RouteLocationRaw }[]>(() => entry.lots.map((lot) => {
  if (lot.acquisition === null)
    return { lot };

  return {
    lot,
    route: {
      name: '/history/events/',
      query: {
        overlay: OverlayMode.COST_BASIS,
        targetGroupIdentifier: lot.acquisition.groupIdentifier,
      },
    },
  };
}));
</script>

<template>
  <div
    class="flex flex-col gap-3"
    data-testid="cost-basis-spend"
  >
    <CostBasisBucketLabel
      :location="entry.location"
      :location-label="entry.locationLabel"
      :method="entry.method"
      :protocol="entry.protocol"
    />

    <dl class="grid grid-cols-[1fr_auto] items-baseline gap-y-1 text-sm tabular-nums [&>dd]:pl-4">
      <template v-if="entry.proceeds !== null">
        <dt class="text-rui-text-secondary">
          {{ t('cost_basis_overlay.proceeds') }}
        </dt>
        <dd
          class="text-right"
          data-testid="cost-basis-proceeds"
        >
          <FiatDisplay
            :value="entry.proceeds"
            :format="COST_BASIS_FIAT_FORMAT"
          />
        </dd>
      </template>
      <dt class="text-rui-text-secondary">
        {{ t('cost_basis_overlay.cost_value') }}
      </dt>
      <dd
        class="text-right"
        data-testid="cost-basis-cost-value"
      >
        <FiatDisplay
          :value="entry.basisRemoved"
          :format="COST_BASIS_FIAT_FORMAT"
        />
      </dd>
      <dt class="pl-3 text-xs text-rui-text-secondary">
        {{ t('cost_basis_overlay.per_unit') }}
      </dt>
      <dd
        class="text-right text-xs text-rui-text-secondary"
        data-testid="cost-basis-basis"
      >
        <FiatDisplay
          :value="basisPerUnit"
          :format="COST_BASIS_FIAT_FORMAT"
        />
      </dd>
      <template
        v-for="(gain, index) in gains"
        :key="gain.key"
      >
        <dt
          class="text-rui-text-secondary"
          :class="{ 'mt-1.5 pt-1.5 border-t border-default': index === 0 }"
        >
          {{ gain.label }}
        </dt>
        <dd
          class="text-right"
          :class="{
            'mt-1.5 pt-1.5 border-t border-default': index === 0,
            'font-semibold': gain.key === 'gain',
          }"
          :data-testid="`cost-basis-${gain.key}`"
        >
          <FiatDisplay
            :value="gain.value"
            :format="COST_BASIS_FIAT_FORMAT"
            pnl
          />
        </dd>
      </template>
    </dl>

    <div
      v-if="!isAverage"
      class="flex flex-col gap-1.5"
      data-testid="cost-basis-lots"
    >
      <div class="flex items-center justify-between text-xs font-medium uppercase tracking-wide text-rui-text-secondary">
        <span>{{ t('cost_basis_overlay.lots') }}</span>
        <span v-if="entry.lots.length > 0">{{ entry.lots.length }}</span>
      </div>
      <p
        v-if="entry.lots.length === 0"
        class="text-xs text-rui-text-secondary"
        data-testid="cost-basis-no-lots"
      >
        {{ t('cost_basis_overlay.no_lots') }}
      </p>
      <div
        v-else
        class="grid grid-cols-[1fr_auto_auto] items-center gap-x-3 text-xs tabular-nums"
      >
        <div
          v-for="({ lot, route }, index) in lots"
          :key="index"
          class="col-span-3 grid grid-cols-subgrid items-center py-1.5"
          :class="{ 'border-t border-default': index > 0 }"
          data-testid="cost-basis-lot"
        >
          <div class="flex items-center gap-1.5 min-w-0">
            <RouterLink
              v-if="route"
              :to="route"
              :title="t('cost_basis_overlay.view_acquisition')"
              class="flex items-center gap-1 text-rui-primary hover:underline"
              data-testid="cost-basis-lot-link"
            >
              <DateDisplay
                :timestamp="lot.acquiredAt"
                no-time
              />
              <RuiIcon
                name="lu-arrow-up-right"
                size="12"
              />
            </RouterLink>
            <DateDisplay
              v-else
              :timestamp="lot.acquiredAt"
              no-time
              class="text-rui-text-secondary"
            />
            <RuiIcon
              v-if="!lot.taxable"
              name="lu-leaf"
              size="12"
              class="text-rui-success shrink-0"
              :aria-label="t('cost_basis_overlay.taxfree')"
              data-testid="cost-basis-lot-taxfree"
            />
          </div>
          <div class="text-right">
            <AssetAmountDisplay
              :amount="lot.amount"
              :asset="entry.asset"
              no-collection-parent
              no-tooltip
            />
          </div>
          <div class="flex items-center justify-end gap-1 text-rui-text-secondary">
            <span class="text-rui-text-disabled">{{ t('cost_basis_overlay.at') }}</span>
            <FiatDisplay
              :value="lot.basisPerUnit"
              :format="COST_BASIS_FIAT_FORMAT"
            />
          </div>
        </div>
      </div>
      <p
        v-if="lots.some(({ lot }) => !lot.taxable)"
        class="flex items-center gap-1 text-xs text-rui-text-secondary"
      >
        <RuiIcon
          name="lu-leaf"
          size="12"
          class="text-rui-success"
        />
        {{ t('cost_basis_overlay.taxfree_legend') }}
      </p>
    </div>
  </div>
</template>
