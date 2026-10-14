<script setup lang="ts">
import type { AccountingOverlayBucket } from '@/modules/history/balances/use-accounting-overlay';
import { type BigNumber, Zero } from '@rotki/common';
import { AssetAmountDisplay, AssetValueDisplay } from '@/modules/assets/amount-display/components';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import AccountingOverlayBucketIcon from '@/modules/history/balances/AccountingOverlayBucketIcon.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import EnsAvatar from '@/modules/shell/components/display/EnsAvatar.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const { buckets, asset, timestamp, account, eventLocation, eventProtocol } = defineProps<{
  buckets: AccountingOverlayBucket[];
  asset: string;
  /** The event's timestamp (ms), shown so the user knows the balance is "as of" this point. */
  timestamp?: number;
  /** The account (address) the buckets belong to, used to label the protocol-less "wallet" row. */
  account?: string;
  /** The triggering event's location, used to highlight the bucket the event actually moved. */
  eventLocation?: string;
  /** The triggering event's counterparty, matched against a bucket's protocol. */
  eventProtocol?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

// A per-protocol breakdown only earns a total row once there is more than one row to sum.
const showTotal = computed<boolean>(() => buckets.length > 1);
const total = computed<BigNumber>(() => buckets.reduce((sum, bucket) => sum.plus(bucket.balance), Zero));

/**
 * The most decimal places any amount is rendered with.
 *
 * @remarks
 * No legitimate asset carries more than this, so a balance exceeding it is almost certainly a
 * broken or hostile token. Such a value is shown rounded rather than in full, and flagged, so one
 * token cannot stretch the column past everything beside it.
 */
const MAX_DISPLAY_DECIMALS = 24;

/** The widest precision actually present among the rows, before the display cap is applied. */
const rawDecimals = computed<number>(() => {
  const values = [...buckets.map(bucket => bucket.balance), get(total)];
  return values.reduce((max, value) => Math.max(max, value.decimalPlaces() ?? 0), 0);
});

/** Shared by every amount, so their decimal points line up down the column. */
const decimals = computed<number>(() => Math.min(get(rawDecimals), MAX_DISPLAY_DECIMALS));

/** Whether what is shown has been rounded, so the user can be told the figure is not exact. */
const excessivePrecision = computed<boolean>(() => get(rawDecimals) > MAX_DISPLAY_DECIMALS);

/**
 * Index of the bucket the triggering event moved, so its row can be highlighted (or -1 for none).
 *
 * The event's counterparty names the protocol it *interacted with*, which is not always where the
 * affected asset's balance lives (e.g. depositing wallet EURe into Aave is an `aave-v3` event, but
 * the EURe that moved came out of the plain wallet). So when exactly one bucket exists, that single
 * position is unambiguously the one that moved and is always highlighted. With several buckets we
 * fall back to a strict chain + protocol match, where a null/'' protocol is the plain wallet.
 */
const affectedIndex = computed<number>(() => {
  if (buckets.length === 1)
    return 0;
  if (!eventLocation)
    return -1;
  return buckets.findIndex(bucket =>
    bucket.location === eventLocation && (bucket.protocol ?? '') === (eventProtocol ?? ''));
});
</script>

<template>
  <div class="flex flex-col gap-3 min-w-56">
    <div class="flex flex-col gap-0.5">
      <div class="flex items-center gap-1">
        <div class="text-xs font-medium text-rui-text-secondary">
          {{ t('accounting_overlay.balance_after') }}
        </div>
        <RuiTooltip
          v-if="excessivePrecision"
          :open-delay="200"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiIcon
              name="lu-triangle-alert"
              size="14"
              class="text-rui-warning"
            />
          </template>
          {{ t('accounting_overlay.high_precision', { decimals: MAX_DISPLAY_DECIMALS }) }}
        </RuiTooltip>
      </div>
      <div class="flex items-center gap-1.5 text-xs text-rui-text-secondary">
        <DateDisplay
          v-if="timestamp"
          :timestamp="timestamp"
          milliseconds
          hide-tooltip
        />
        <template v-if="account">
          <span
            v-if="timestamp"
            class="size-0.5 rounded-full bg-current"
          />
          <EnsAvatar
            :address="account"
            avatar
            size="14px"
          />
          <span
            class="font-mono"
            :title="account"
          >
            {{ account.slice(0, 8) }}
          </span>
        </template>
      </div>
    </div>
    <div class="flex flex-col gap-1">
      <div
        v-for="(bucket, i) in buckets"
        :key="i"
        class="flex items-center justify-between gap-6 text-sm -mx-1.5 px-1.5 py-1 rounded-sm"
        :class="i === affectedIndex
          ? 'bg-rui-primary/5 ring-1 ring-inset ring-rui-primary/20'
          : undefined"
      >
        <div
          class="flex items-center gap-2 min-w-0"
          :class="i === affectedIndex ? 'font-medium text-rui-text' : 'text-rui-text-secondary'"
        >
          <LocationIcon
            :item="bucket.location"
            icon
            size="16px"
          />
          <span class="truncate">{{ getChainName(bucket.location) }}</span>
          <span class="flex items-center gap-1 min-w-0 text-xs font-normal text-rui-text-disabled">
            <AccountingOverlayBucketIcon
              v-if="bucket.protocol"
              :protocol="bucket.protocol"
              size="12"
            />
            <RuiIcon
              v-else
              name="lu-wallet"
              size="12"
              class="shrink-0"
            />
            <span class="truncate">{{ bucket.protocol ?? t('accounting_overlay.wallet') }}</span>
          </span>
        </div>
        <div
          class="flex flex-col items-end shrink-0"
          :class="{ 'text-rui-text-disabled': bucket.balance.isZero() }"
        >
          <AssetAmountDisplay
            :amount="bucket.balance"
            :asset="asset"
            :decimals="bucket.balance.isZero() ? 0 : decimals"
            no-collection-parent
            no-tooltip
            class="text-xs font-medium tabular-nums"
          />
          <AssetValueDisplay
            v-if="timestamp"
            :amount="bucket.balance"
            :asset="asset"
            :value="Zero"
            :timestamp="{ ms: timestamp }"
            no-collection-parent
            class="text-xs text-rui-text-secondary tabular-nums"
          />
        </div>
      </div>
    </div>
    <template v-if="showTotal">
      <RuiDivider />
      <div class="flex items-center justify-between gap-6 text-sm font-medium">
        <span>{{ t('accounting_overlay.total') }}</span>
        <div class="flex flex-col items-end shrink-0">
          <AssetAmountDisplay
            :amount="total"
            :asset="asset"
            :decimals="decimals"
            no-collection-parent
            no-tooltip
            class="text-xs tabular-nums"
          />
          <AssetValueDisplay
            v-if="timestamp"
            :amount="total"
            :asset="asset"
            :value="Zero"
            :timestamp="{ ms: timestamp }"
            no-collection-parent
            class="text-xs text-rui-text-secondary tabular-nums"
          />
        </div>
      </div>
    </template>
  </div>
</template>
