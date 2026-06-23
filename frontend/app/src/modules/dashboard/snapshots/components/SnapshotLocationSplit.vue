<script setup lang="ts">
import { type BigNumber, bigNumberify, Zero } from '@rotki/common';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { convertFiatToUsd, convertUsdToFiat } from '@/modules/dashboard/snapshots/utils/snapshot-fx';
import { approxEqualUsd, type LocationSplit } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

/** The resolved split in USD; the first row absorbs rounding so it sums to `total`. */
const splits = defineModel<LocationSplit[]>({ required: true });
/** Whether the split is complete (every row filled, no dupes, sums to `total`). */
const valid = defineModel<boolean>('valid', { default: false });

const { locations, maxPerLocation = {}, timestamp, total } = defineProps<{
  /** The balance's full USD value that the split must add up to. */
  total: BigNumber;
  timestamp: number;
  /** Existing location names, offered as suggestions. */
  locations: string[];
  /**
   * Current USD subtotal of each location, the most a row may remove from it.
   * Empty for additive splits (add); set for removals so a portion can't drive a
   * location negative.
   */
  maxPerLocation?: Record<string, BigNumber>;
}>();

/** A single split row; `amount` is entered in the display (fiat) currency. */
interface SplitRow {
  location: string;
  amount: string;
}

const { t } = useI18n({ useScope: 'global' });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { isUsd, rate } = useHistoricFiatConversion(() => timestamp);

const rows = ref<SplitRow[]>([{ amount: '', location: '' }, { amount: '', location: '' }]);

/** Converts a display-currency input back into the stored USD value. */
function toUsd(amount: string): BigNumber {
  const value = bigNumberify(amount || '0');
  return get(isUsd) ? value : convertFiatToUsd(value, get(rate));
}

const targetFiat = computed<BigNumber>(() => get(isUsd) ? total : convertUsdToFiat(total, get(rate)));
const allocatedUsd = computed<BigNumber>(() => get(rows).reduce((sum, row) => sum.plus(toUsd(row.amount)), Zero));
const remainingUsd = computed<BigNumber>(() => total.minus(get(allocatedUsd)));

/** The location's USD cap for a row, or undefined when uncapped (additive split). */
function capFor(location: string): BigNumber | undefined {
  return location ? maxPerLocation[location] : undefined;
}

/** The location's resulting subtotal after this row's removal (capped rows only). */
function remainingFor(row: SplitRow): BigNumber | null {
  const cap = capFor(row.location);
  return cap ? cap.minus(toUsd(row.amount)) : null;
}

/** A row exceeds its location's cap when it would remove more than it holds. */
function exceedsCap(row: SplitRow): boolean {
  const remaining = remainingFor(row);
  return remaining !== null && remaining.isNegative();
}

const isValid = computed<boolean>(() => {
  const current = get(rows);
  if (current.some(row => !row.location || !row.amount))
    return false;
  const names = current.map(row => row.location);
  if (new Set(names).size !== names.length)
    return false;
  if (current.some(row => exceedsCap(row)))
    return false;
  return approxEqualUsd(get(allocatedUsd), total);
});

/**
 * The split in USD. Every row but the first converts its fiat input directly; the
 * first row takes whatever is left of `total`, so the portions always sum exactly
 * to the balance's value (no fiat-round-trip drift breaking reconciliation).
 */
const result = computed<LocationSplit[]>(() => {
  const current = get(rows);
  const rest = current.slice(1).reduce((sum, row) => sum.plus(toUsd(row.amount)), Zero);
  return current.map((row, index) => ({
    location: row.location,
    usdValue: index === 0 ? total.minus(rest) : toUsd(row.amount),
  }));
});

function addRow(): void {
  set(rows, [...get(rows), { amount: '', location: '' }]);
}

function removeRow(index: number): void {
  const current = [...get(rows)];
  current.splice(index, 1);
  set(rows, current);
}

/** Spreads the target value evenly across the current rows. */
function distribute(): void {
  const current = get(rows);
  const each = get(targetFiat).dividedBy(current.length).toFixed(2);
  set(rows, current.map(row => ({ ...row, amount: each })));
}

watch([result, isValid], () => {
  set(splits, get(result));
  set(valid, get(isValid));
}, { deep: true, immediate: true });
</script>

<template>
  <div
    class="flex flex-col gap-3"
    data-testid="snapshot-location-split"
  >
    <div class="flex items-center justify-between">
      <div class="text-subtitle-2">
        {{ t('dashboard.snapshot.detail.split.title') }}
      </div>
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        data-testid="snapshot-location-split-distribute"
        @click="distribute()"
      >
        {{ t('dashboard.snapshot.detail.split.distribute') }}
      </RuiButton>
    </div>

    <p class="text-caption text-rui-text-secondary">
      {{ t('dashboard.snapshot.detail.split.hint') }}
    </p>

    <div
      v-for="(row, index) in rows"
      :key="index"
      class="flex flex-col gap-1"
      data-testid="snapshot-location-split-row"
    >
      <div class="flex items-start gap-2">
        <LocationSelector
          v-model="row.location"
          class="flex-1"
          :items="locations"
          clearable
          dense
          :menu-options="{ menuClass: 'z-[10001]' }"
          hide-details
          :label="t('common.location')"
          data-testid="snapshot-location-split-location"
        />
        <AmountInput
          v-model="row.amount"
          variant="outlined"
          dense
          hide-details
          class="w-40"
          :label="t('common.value_in_symbol', { symbol: currencySymbol })"
          data-testid="snapshot-location-split-amount"
        />
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="mt-1"
          :disabled="rows.length <= 1"
          @click="removeRow(index)"
        >
          <RuiIcon
            name="lu-trash-2"
            size="18"
          />
        </RuiButton>
      </div>
      <div
        v-if="capFor(row.location)"
        class="text-caption flex items-center gap-1 pl-1 text-rui-text-secondary"
        data-testid="snapshot-location-split-remaining-row"
      >
        {{ t('dashboard.snapshot.detail.split.available') }}
        <SnapshotFiatDisplay
          class="font-medium"
          :value="capFor(row.location)!"
          :timestamp="timestamp"
        />
        <span class="border-l border-rui-text-disabled h-3 mx-1" />
        {{ t('dashboard.snapshot.detail.split.location_after') }}
        <SnapshotFiatDisplay
          class="font-medium"
          :class="{ 'text-rui-error': exceedsCap(row) }"
          :value="remainingFor(row)!"
          :timestamp="timestamp"
        />
      </div>
    </div>

    <div class="flex items-center justify-between">
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        data-testid="snapshot-location-split-add"
        @click="addRow()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-circle-plus"
            size="18"
          />
        </template>
        {{ t('dashboard.snapshot.detail.split.add_row') }}
      </RuiButton>
      <div
        class="text-body-2"
        :class="valid ? 'text-rui-success' : 'text-rui-text-secondary'"
        data-testid="snapshot-location-split-remaining"
      >
        {{ t('dashboard.snapshot.detail.split.remaining') }}:
        <SnapshotFiatDisplay
          class="font-medium"
          :value="remainingUsd"
          :timestamp="timestamp"
        />
      </div>
    </div>
  </div>
</template>
