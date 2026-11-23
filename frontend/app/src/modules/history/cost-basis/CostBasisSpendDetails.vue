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
  pnl: boolean;
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
 * The figures of the spend, top to bottom.
 *
 * @remarks
 * A move between two own accounts or an unpriced spend has no proceeds or realized gain, so only
 * the cost basis per unit and the cost value are shown. A tax free gain of zero is omitted.
 */
const figures = computed<FigureRow[]>(() => {
  const rows: FigureRow[] = [
    { key: 'basis', label: t('cost_basis_overlay.cost_basis'), pnl: false, value: get(basisPerUnit) },
    { key: 'cost-value', label: t('cost_basis_overlay.cost_value'), pnl: false, value: entry.basisRemoved },
  ];
  if (entry.proceeds !== null && entry.realizedPnl !== null)
    rows.push({ key: 'gain', label: t('cost_basis_overlay.gain'), pnl: true, value: entry.realizedPnl });
  if (entry.taxfreePnl !== null && !entry.taxfreePnl.isZero())
    rows.push({ key: 'taxfree-gain', label: t('cost_basis_overlay.taxfree_gain'), pnl: true, value: entry.taxfreePnl });
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
    class="flex flex-col gap-3 min-w-80"
    data-testid="cost-basis-spend"
  >
    <CostBasisBucketLabel
      :location="entry.location"
      :location-label="entry.locationLabel"
      :protocol="entry.protocol"
    />
    <div class="flex flex-col gap-1 text-sm">
      <div
        v-for="figure in figures"
        :key="figure.key"
        class="flex items-center justify-between gap-6"
        :data-testid="`cost-basis-${figure.key}`"
      >
        <span class="text-rui-text-secondary">{{ figure.label }}</span>
        <FiatDisplay
          :value="figure.value"
          :format="COST_BASIS_FIAT_FORMAT"
          :pnl="figure.pnl"
          class="font-medium tabular-nums"
        />
      </div>
    </div>
    <template v-if="!isAverage">
      <RuiDivider />
      <div
        class="flex flex-col gap-1 text-xs"
        data-testid="cost-basis-lots"
      >
        <span class="text-sm font-medium">{{ t('cost_basis_overlay.lots') }}</span>
        <span
          v-if="entry.lots.length === 0"
          class="text-rui-text-secondary max-w-80"
          data-testid="cost-basis-no-lots"
        >
          {{ t('cost_basis_overlay.no_lots') }}
        </span>
        <div
          v-for="({ lot, route }, index) in lots"
          :key="index"
          class="flex items-center justify-between gap-6 py-0.5"
          data-testid="cost-basis-lot"
        >
          <div class="flex items-center gap-1.5 min-w-0">
            <DateDisplay
              :timestamp="lot.acquiredAt"
              class="text-rui-text-secondary"
            />
            <RouterLink
              v-if="route"
              :to="route"
              :aria-label="t('cost_basis_overlay.view_acquisition')"
              class="flex text-rui-primary"
              data-testid="cost-basis-lot-link"
            >
              <RuiIcon
                name="lu-external-link"
                size="12"
              />
            </RouterLink>
            <RuiChip
              v-if="!lot.taxable"
              size="sm"
              color="success"
              variant="outlined"
              data-testid="cost-basis-lot-taxfree"
            >
              {{ t('cost_basis_overlay.taxfree') }}
            </RuiChip>
          </div>
          <div class="flex items-center gap-1.5 shrink-0 tabular-nums">
            <AssetAmountDisplay
              :amount="lot.amount"
              :asset="entry.asset"
              no-collection-parent
              no-tooltip
            />
            <span class="text-rui-text-disabled">{{ t('cost_basis_overlay.at') }}</span>
            <FiatDisplay
              :value="lot.basisPerUnit"
              :format="COST_BASIS_FIAT_FORMAT"
              class="text-rui-text-secondary"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
