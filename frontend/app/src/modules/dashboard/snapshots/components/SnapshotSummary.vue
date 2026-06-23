<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { Snapshot } from '@/modules/dashboard/snapshots';
import type { SnapshotSumMismatch } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { isNft } from '@/modules/assets/nft-utils';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import SnapshotFiatDisplay from '@/modules/dashboard/snapshots/components/SnapshotFiatDisplay.vue';
import SnapshotFxOverrideControl from '@/modules/dashboard/snapshots/components/SnapshotFxOverrideControl.vue';
import { useSnapshotAssetFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters';
import { getTotalValue, locationsTotal, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import { getSnapshotWarnings, type SnapshotWarning } from '@/modules/dashboard/snapshots/utils/snapshot-warnings';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const excludeNfts = defineModel<boolean>('excludeNfts', { default: false });

const {
  mismatch = null,
  previous,
  snapshot,
  timestamp,
} = defineProps<{
  /** The draft snapshot; net worth, allocation and warnings derive from it. */
  snapshot: Snapshot;
  timestamp: number;
  /** The draft's NFT-aware sum mismatch, surfaced as the reconcile banner. */
  mismatch?: SnapshotSumMismatch | null;
  /** Previous snapshot's stored total (USD) and timestamp, for the delta line. */
  previous?: { value: BigNumber; timestamp: number };
}>();

const emit = defineEmits<{
  'edit-locations': [];
  'reconcile-locations': [location: string];
}>();

/** Number of location rows shown in the allocation glance before "+N more". */
const ALLOCATION_LIMIT = 4;

const { t } = useI18n({ useScope: 'global' });

const { isSpamAsset } = useSnapshotAssetFilters();

const netWorth = computed<BigNumber>(() => getTotalValue(snapshot.locationDataSnapshot));
const hasNfts = computed<boolean>(() => snapshot.balancesSnapshot.some(item => isNft(item.assetIdentifier)));

/** Real (non-`total`) location rows, the candidates for absorbing a reconcile. */
const existingLocations = computed<string[]>(() =>
  snapshot.locationDataSnapshot.filter(item => item.location !== TOTAL_LOCATION).map(item => item.location),
);

/** The biggest location by value — pre-selected to absorb the reconcile difference. */
const largestLocation = computed<string>(() => {
  const rows = snapshot.locationDataSnapshot.filter(item => item.location !== TOTAL_LOCATION);
  if (rows.length === 0)
    return '';
  return rows.reduce((max, item) => (item.usdValue.gt(max.usdValue) ? item : max)).location;
});

/** Which location absorbs the difference; defaults to the largest, user can switch. */
const reconcileLocation = ref<string>('');
watchImmediate(largestLocation, (location) => {
  if (!get(reconcileLocation))
    set(reconcileLocation, location);
});
const warnings = computed<SnapshotWarning[]>(() =>
  getSnapshotWarnings(snapshot, { isSpam: isSpamAsset, previousTotal: previous?.value }),
);

const delta = computed<BigNumber | undefined>(() => {
  if (previous === undefined)
    return undefined;
  return get(netWorth).minus(previous.value);
});

const deltaPercent = computed<string | undefined>(() => {
  const diff = get(delta);
  if (diff === undefined || previous === undefined || previous.value.isZero())
    return undefined;
  return diff.dividedBy(previous.value).multipliedBy(100).toFormat(2);
});

interface AllocationSegment {
  location: string;
  percent: number;
  /** Aggregate bucket for sub-1% / overflow locations. */
  other: boolean;
}

/** Distinct (non-alarming) colours cycled across the allocation segments. */
const SEGMENT_COLORS = ['bg-rui-primary', 'bg-rui-info', 'bg-rui-success', 'bg-rui-secondary'] as const;

const allocation = computed<{ location: string; percent: number }[]>(() => {
  const total = locationsTotal(snapshot.locationDataSnapshot);
  if (total.isZero())
    return [];
  return snapshot.locationDataSnapshot
    .filter(item => item.location !== TOTAL_LOCATION)
    .map(item => ({ location: item.location, percent: item.usdValue.dividedBy(total).multipliedBy(100).toNumber() }))
    .sort((a, b) => b.percent - a.percent);
});

// The named segments shown in the bar/legend: the largest locations, with the
// long tail of tiny (<1%) and overflow locations folded into a single "Other"
// bucket so the row isn't cluttered with a string of 0% entries.
const allocationSegments = computed<AllocationSegment[]>(() => {
  const top = get(allocation).filter(entry => entry.percent >= 1).slice(0, ALLOCATION_LIMIT);
  const segments: AllocationSegment[] = top.map(entry => ({ location: entry.location, other: false, percent: Math.round(entry.percent) }));
  const remainder = 100 - top.reduce((sum, entry) => sum + entry.percent, 0);
  if (remainder >= 1)
    segments.push({ location: 'other', other: true, percent: Math.round(remainder) });
  return segments;
});

function segmentColor(index: number, other: boolean): string {
  return other ? 'bg-rui-grey-400' : SEGMENT_COLORS[index % SEGMENT_COLORS.length];
}

function warningMessage(warning: SnapshotWarning): string {
  const asset = warning.asset ?? '';
  switch (warning.code) {
    case 'negative-balance':
      return t('dashboard.snapshot.detail.warnings.negative_balance', { asset });
    case 'duplicate-asset':
      return t('dashboard.snapshot.detail.warnings.duplicate_asset', { asset });
    case 'nft-amount':
      return t('dashboard.snapshot.detail.warnings.nft_amount', { asset });
    case 'net-worth-swing':
      return t('dashboard.snapshot.detail.warnings.net_worth_swing', { percent: (warning.swingPercent ?? 0).toFixed(0) });
  }
  return '';
}

// Zero-value rows are overwhelmingly valueless spam/airdrop tokens, not edit
// mistakes — listing each would bury the genuine warnings. Collapse them into a
// single count and keep every other warning one-to-one.
const warningMessages = computed<string[]>(() => {
  const all = get(warnings);
  const messages = all.filter(warning => warning.code !== 'zero-value').map(warningMessage);
  const zeroValueCount = all.filter(warning => warning.code === 'zero-value').length;
  if (zeroValueCount > 0)
    messages.push(t('dashboard.snapshot.detail.warnings.zero_value', { count: zeroValueCount }, zeroValueCount));
  return messages;
});

// The sanity warnings are advisory, so let the user dismiss them. Re-surface when
// the set of warnings changes (an edit introduced or resolved something).
const warningsDismissed = ref<boolean>(false);
watch(() => get(warningMessages).join(' '), () => {
  set(warningsDismissed, false);
});
</script>

<template>
  <RuiCard data-testid="snapshot-summary">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div class="text-caption text-rui-text-secondary">
          {{ t('dashboard.snapshot.detail.summary.net_worth') }}
        </div>
        <!-- Reserve the text-h4 line height (2.625rem) so the loading skeleton
             doesn't shift the layout when the converted value resolves. -->
        <div class="min-h-[2.625rem] flex items-center">
          <SnapshotFiatDisplay
            class="text-h4"
            :value="netWorth"
            :timestamp="timestamp"
            data-testid="snapshot-summary-net-worth"
          />
        </div>
        <div
          v-if="delta && previous"
          class="text-body-2 mt-1 flex items-center gap-1"
          :class="delta.isNegative() ? 'text-rui-error' : 'text-rui-success'"
          data-testid="snapshot-summary-delta"
        >
          <RuiIcon
            :name="delta.isNegative() ? 'lu-trending-down' : 'lu-trending-up'"
            size="16"
          />
          <SnapshotFiatDisplay
            :value="delta"
            :timestamp="timestamp"
          />
          <span v-if="deltaPercent">{{ t('dashboard.snapshot.detail.summary.delta_percent', { percent: deltaPercent }) }}</span>
          <span class="text-rui-text-secondary">
            {{ t('dashboard.snapshot.detail.summary.since') }}
            <DateDisplay
              :timestamp="previous.timestamp"
              class="inline"
            />
          </span>
        </div>
      </div>

      <div
        v-if="hasNfts"
        class="flex flex-col items-end gap-2 min-w-[14rem]"
      >
        <RuiCheckbox
          v-model="excludeNfts"
          color="primary"
          hide-details
          size="sm"
          data-testid="snapshot-summary-exclude-nfts"
        >
          {{ t('dashboard.snapshot.detail.summary.exclude_nfts') }}
        </RuiCheckbox>
      </div>
    </div>

    <SnapshotFxOverrideControl
      :timestamp="timestamp"
      class="mt-3"
    />

    <div
      v-if="allocation.length > 0"
      class="mt-3"
      data-testid="snapshot-summary-allocation"
    >
      <div class="flex items-center justify-between gap-2 mb-2">
        <span class="text-rui-text-secondary text-body-2">{{ t('dashboard.snapshot.detail.summary.allocation') }}</span>
        <RuiButton
          variant="text"
          size="sm"
          color="primary"
          data-testid="snapshot-summary-edit-locations"
          @click="emit('edit-locations')"
        >
          {{ t('dashboard.snapshot.detail.summary.edit_locations') }}
          <template #append>
            <RuiIcon
              name="lu-chevron-right"
              size="16"
            />
          </template>
        </RuiButton>
      </div>
      <div class="flex h-2 rounded-full overflow-hidden bg-rui-grey-100 dark:bg-rui-grey-800">
        <div
          v-for="(segment, index) in allocationSegments"
          :key="segment.location"
          class="h-full first:rounded-l-full last:rounded-r-full"
          :class="segmentColor(index, segment.other)"
          :style="{ width: `${segment.percent}%` }"
        />
      </div>
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-2 text-body-2">
        <span
          v-for="(segment, index) in allocationSegments"
          :key="segment.location"
          class="flex items-center gap-1.5"
        >
          <span
            class="size-2 rounded-full shrink-0"
            :class="segmentColor(index, segment.other)"
          />
          <LocationDisplay
            v-if="!segment.other"
            :opens-details="false"
            :identifier="segment.location"
          />
          <span
            v-else
            class="text-rui-text-secondary"
          >
            {{ t('dashboard.snapshot.detail.summary.allocation_other') }}
          </span>
          <span class="font-medium">{{ t('dashboard.snapshot.detail.summary.allocation_percent', { percent: segment.percent }) }}</span>
        </span>
      </div>
    </div>

    <RuiAlert
      v-if="mismatch"
      type="warning"
      class="mt-3"
      data-testid="snapshot-summary-reconcile"
    >
      <template #title>
        {{ t('dashboard.snapshot.detail.mismatch.title') }}
      </template>
      <p class="text-body-2 mb-2">
        {{ t('dashboard.snapshot.detail.mismatch.description') }}
      </p>
      <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3 text-body-2">
        <span>
          {{ t('dashboard.snapshot.detail.mismatch.balances_sum') }}:
          <SnapshotFiatDisplay
            class="font-medium"
            :value="mismatch.balancesSum"
            :timestamp="timestamp"
          />
        </span>
        <span>
          {{ t('dashboard.snapshot.detail.mismatch.locations_sum') }}:
          <SnapshotFiatDisplay
            class="font-medium"
            :value="mismatch.locationsSum"
            :timestamp="timestamp"
          />
        </span>
      </div>
      <div
        v-if="existingLocations.length > 0"
        class="flex flex-wrap items-end gap-2 mb-3"
      >
        <LocationSelector
          v-model="reconcileLocation"
          class="w-60"
          :items="existingLocations"
          dense
          hide-details
          :label="t('dashboard.snapshot.detail.mismatch.reconcile_into')"
        />
        <RuiButton
          size="sm"
          color="warning"
          :disabled="!reconcileLocation"
          data-testid="snapshot-summary-reconcile-apply"
          @click="emit('reconcile-locations', reconcileLocation)"
        >
          {{ t('dashboard.snapshot.detail.mismatch.reconcile_apply') }}
        </RuiButton>
      </div>

      <div class="flex flex-wrap gap-2">
        <RuiButton
          size="sm"
          color="warning"
          variant="outlined"
          data-testid="snapshot-summary-edit-locations-reconcile"
          @click="emit('edit-locations')"
        >
          {{ t('dashboard.snapshot.detail.summary.edit_locations') }}
        </RuiButton>
      </div>
    </RuiAlert>

    <RuiAlert
      v-if="warningMessages.length > 0 && !warningsDismissed"
      type="warning"
      class="mt-3"
      closeable
      data-testid="snapshot-summary-warnings"
      @close="warningsDismissed = true"
    >
      <template #title>
        {{ t('dashboard.snapshot.detail.warnings.title') }}
      </template>
      <ul class="list-disc pl-4 text-body-2">
        <li
          v-for="(message, index) in warningMessages"
          :key="index"
        >
          {{ message }}
        </li>
      </ul>
    </RuiAlert>
  </RuiCard>
</template>
