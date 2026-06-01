<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { HistoryEventEntry, HistoryEventState } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventStateChip from '@/modules/history/events/HistoryEventStateChip.vue';
import HistoryEventTypeCombination from '@/modules/history/events/HistoryEventTypeCombination.vue';
import HistoryEventTypeCounterparty from '@/modules/history/events/HistoryEventTypeCounterparty.vue';
import HistoryEventTypeLocationBadge from '@/modules/history/events/HistoryEventTypeLocationBadge.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

const { event, groupLocationLabel, icon, highlight, hideStateChips, matchedMovement } = defineProps<{
  event: HistoryEventEntry;
  groupLocationLabel?: string;
  icon?: RuiIcons;
  highlight?: boolean;
  hideStateChips?: boolean;
  /** Set when the event is rendered inside an expanded linked (matched) movement. */
  matchedMovement?: boolean;
}>();

const { getEventTypeData } = useHistoryEventMappings();
const { matchChain } = useSupportedChains();

const attrs = getEventTypeData(() => event);

const counterparty = computed<string | undefined>(() =>
  'counterparty' in event ? (event.counterparty ?? undefined) : undefined,
);

const address = computed<string | undefined>(() =>
  'address' in event ? (event.address ?? undefined) : undefined,
);

const isInformational = computed<boolean>(() => event.eventType === 'informational');

// Whether the event's own location is an exchange (e.g. kraken) rather than a blockchain.
const isExchangeLocation = computed<boolean>(() => !matchChain(event.location));

const hasCounterpartyBadge = computed<boolean>(() => !!get(counterparty) || !!get(address));

// The exchange-side leg of a linked movement: the asset movement at the exchange location.
const isExchangeMovementLeg = computed<boolean>(() =>
  !!matchedMovement
  && get(isExchangeLocation)
  && event.entryType === HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
);

// The on-chain leg of a linked movement: the transfer that happened on a blockchain.
const isOnChainLeg = computed<boolean>(() => !!matchedMovement && !get(isExchangeLocation));

// Surface a location icon on each leg: the exchange icon on the exchange-side asset movement,
// and the chain icon on the on-chain leg.
const showLocationBadge = computed<boolean>(() => get(isExchangeMovementLeg) || get(isOnChainLeg));

// The on-chain leg carries a synthetic counterparty pointing at the exchange. Suppress it so
// the chain icon shows on that leg instead.
const showCounterpartyBadge = computed<boolean>(() =>
  get(hasCounterpartyBadge) && !get(isOnChainLeg),
);

const eventStates = computed<HistoryEventState[]>(() => event.states ?? []);

const showLocationLabel = computed<boolean>(() => {
  const eventLabel = event.locationLabel;
  if (!eventLabel)
    return false;

  // Show only when different from group (or no group context)
  return !groupLocationLabel || eventLabel !== groupLocationLabel;
});
</script>

<template>
  <div
    data-cy="event-type"
    class="flex items-center text-left min-w-0"
  >
    <HistoryEventTypeCounterparty
      v-if="showCounterpartyBadge"
      :counterparty="counterparty"
      :address="address"
      :location="event.location"
      class="shrink-0"
    >
      <HistoryEventTypeCombination
        :highlight="highlight"
        :icon="icon"
        :type="attrs"
        :show-info="isInformational"
      />
    </HistoryEventTypeCounterparty>
    <HistoryEventTypeLocationBadge
      v-else-if="showLocationBadge"
      :location="event.location"
      class="shrink-0"
    >
      <HistoryEventTypeCombination
        :highlight="highlight"
        :icon="icon"
        :type="attrs"
        :show-info="isInformational"
      />
    </HistoryEventTypeLocationBadge>
    <HistoryEventTypeCombination
      v-else
      :highlight="highlight"
      :icon="icon"
      :type="attrs"
      :show-info="isInformational"
      class="shrink-0"
    />

    <div class="ml-3 min-w-0">
      <div class="font-medium uppercase text-sm truncate">
        {{ attrs.label }}
      </div>
      <HistoryEventAccount
        v-if="showLocationLabel"
        :location="event.location"
        :location-label="event.locationLabel!"
        class="text-rui-text-secondary"
      />
      <div
        v-if="eventStates.length > 0 && !hideStateChips"
        class="flex flex-wrap gap-0.5"
      >
        <HistoryEventStateChip
          v-for="state in eventStates"
          :key="state"
          :state="state"
        />
      </div>
    </div>
  </div>
</template>
