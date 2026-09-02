<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AccountingOverlayBuckets from '@/modules/history/balances/AccountingOverlayBuckets.vue';
import AccountingOverlaySparkline from '@/modules/history/balances/AccountingOverlaySparkline.vue';
import { type AccountingOverlayBucket, PairOverlayStatus, type SparklinePoint } from '@/modules/history/balances/use-accounting-overlay';
import { injectAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay-context';
import { type EventDirection, getEventDirectionIcon, getEventDirectionTextClass } from '@/modules/history/events/event-direction';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

const { event } = defineProps<{ event: HistoryEventEntry }>();

const { t } = useI18n({ useScope: 'global' });
const context = injectAccountingOverlay();
const { getEventTypeData } = useHistoryEventMappings();

const eventTypeData = getEventTypeData(() => event);
const direction = computed<EventDirection>(() => get(eventTypeData).direction);
const showDelta = computed<boolean>(() => get(direction) !== 'neutral' && event.amount.gt(0));

const enabled = computed<boolean>(() => !!context && get(context.enabled));
const account = computed<string | undefined>(() => event.locationLabel ?? undefined);
/**
 * The bucket protocol this event moved, so the breakdown can highlight that position.
 *
 * @remarks
 * Undefined means the plain wallet bucket. Gas reaches here as a counterparty but is paid out of
 * the wallet rather than a held protocol position, so it resolves to the wallet too.
 */
const eventProtocol = computed<string | undefined>(() => {
  const counterparty = 'counterparty' in event ? event.counterparty : undefined;
  if (!counterparty || counterparty === 'gas')
    return undefined;
  return counterparty;
});

const status = computed<PairOverlayStatus | undefined>(() => {
  const acct = get(account);
  if (!context || !acct)
    return undefined;
  return context.overlay.statusFor(acct, event.asset);
});

const balance = computed<BigNumber | undefined>(() => {
  const acct = get(account);
  if (!context || !acct)
    return undefined;
  return context.overlay.balanceAfter(acct, event.asset, event.timestamp);
});

const buckets = computed<AccountingOverlayBucket[]>(() => {
  const acct = get(account);
  if (!context || !acct)
    return [];
  return context.overlay.bucketsAt(acct, event.asset, event.timestamp);
});

// Balance trajectory up to this event for the breakdown sparkline (premium-gated in the component).
const series = computed<SparklinePoint[]>(() => {
  const acct = get(account);
  if (!context || !acct)
    return [];
  return context.overlay.seriesUpTo(acct, event.asset, event.timestamp);
});

watchEffect(() => {
  const acct = get(account);
  if (context && get(enabled) && acct && event.asset)
    context.overlay.ensurePair({ asset: event.asset, locationLabel: acct, location: event.location });
});

/** Why this row shows a dash rather than a balance, or undefined once one is available. */
const placeholder = computed<string | undefined>(() => {
  if (!get(account))
    return t('accounting_overlay.no_account');
  if (get(status) === PairOverlayStatus.EMPTY || get(balance) === undefined)
    return t('accounting_overlay.no_balance');
  return undefined;
});
</script>

<template>
  <div
    v-if="enabled"
    class="w-32 xl:w-40 shrink-0 flex items-center justify-end text-sm"
    data-testid="accounting-overlay-cell"
  >
    <RuiSkeletonLoader
      v-if="status === PairOverlayStatus.LOADING"
      class="w-20 h-4"
    />

    <RuiTooltip
      v-else-if="status === PairOverlayStatus.PROCESSING"
      :open-delay="200"
    >
      <template #activator>
        <RuiIcon
          name="lu-loader"
          class="text-rui-warning"
          size="16"
        />
      </template>
      {{ t('accounting_overlay.processing') }}
    </RuiTooltip>

    <RuiTooltip
      v-else-if="status === PairOverlayStatus.ERROR"
      :open-delay="200"
    >
      <template #activator>
        <RuiIcon
          name="lu-circle-alert"
          class="text-rui-error"
          size="16"
        />
      </template>
      {{ t('accounting_overlay.error') }}
    </RuiTooltip>

    <!-- No balance: a dash where the amount would be, with the info anchor on the right — both
         align vertically with the populated rows. -->
    <div
      v-else-if="placeholder"
      class="flex items-center justify-end gap-1.5"
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
            class="text-rui-text-secondary cursor-help shrink-0"
          />
        </template>
        {{ placeholder }}
      </RuiTooltip>
    </div>

    <div
      v-else-if="balance !== undefined"
      class="flex items-center justify-end gap-1.5"
    >
      <div class="flex flex-col items-end leading-tight">
        <AssetAmountDisplay
          :amount="balance"
          :asset="event.asset"
          no-collection-parent
          class="font-medium"
        />
        <span
          v-if="showDelta"
          class="flex items-center gap-0.5 text-xs"
          :class="getEventDirectionTextClass(direction)"
          data-testid="overlay-delta"
        >
          <RuiIcon
            :name="getEventDirectionIcon(direction)"
            size="12"
          />
          <AssetAmountDisplay
            :amount="event.amount"
            no-collection-parent
          />
        </span>
      </div>
      <!-- Hover to peek, click to pin: a RuiMenu (not a tooltip) so the breakdown stays open for
           reading/touch and the trigger is a focusable, keyboard-operable button. -->
      <RuiMenu
        open-on-hover
        :close-delay="200"
        :close-on-content-click="false"
        :options="{ placement: 'left', strategy: 'fixed', autoUpdate: { resize: false, scroll: false } }"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="!p-0.5 shrink-0"
            :aria-label="t('accounting_overlay.show_breakdown')"
            v-bind="attrs"
          >
            <RuiIcon
              name="lu-info"
              size="14"
              class="text-rui-text-secondary"
            />
          </RuiButton>
        </template>
        <div class="p-3 flex flex-col gap-2">
          <AccountingOverlaySparkline :points="series" />
          <AccountingOverlayBuckets
            :buckets="buckets"
            :asset="event.asset"
            :timestamp="event.timestamp"
            :account="account"
            :event-location="event.location"
            :event-protocol="eventProtocol"
          />
        </div>
      </RuiMenu>
    </div>
  </div>
</template>
