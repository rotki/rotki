<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { Blockchain, toSentenceCase } from '@rotki/common';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEventsIdentifier } from '@/modules/history/events/use-history-events-identifier';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { event, groupEvents, revealActions = false } = defineProps<{
  event: HistoryEventEntry;
  groupEvents?: HistoryEventEntry[];
  /** Hides the links' copy and explorer buttons until the link or its `group/row` is hovered or focused. */
  revealActions?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const hashMenuOpen = ref<boolean>(false);

const {
  allTxRefs,
  assetMovementEvent,
  assetMovementTransactionId,
  blockEvent,
  eventWithTxRef,
  extraHashCount,
  key,
  translationKey,
  truncateLength,
  withdrawEvent,
} = useHistoryEventsIdentifier(() => event, () => groupEvents);

const { useLocationData } = useLocations();
const locationData = useLocationData(() => event.location);

/** The location's display name, falling back to its identifier until location data has loaded. */
const locationName = computed<string>(() => get(locationData)?.name ?? toSentenceCase(event.location));
</script>

<template>
  <i18n-t
    :key="key"
    scope="global"
    :keypath="translationKey"
    tag="div"
    class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm"
  >
    <template #location>
      {{ locationName }}
    </template>

    <template
      v-if="blockEvent"
      #blockNumber
    >
      <HashLink
        :text="blockEvent.blockNumber.toString()"
        type="block"
        :reveal-actions="revealActions"
      />
    </template>

    <template
      v-if="withdrawEvent"
      #validatorIndex
    >
      <HashLink
        :text="withdrawEvent.validatorIndex.toString()"
        :location="Blockchain.ETH2"
        :reveal-actions="revealActions"
      />
    </template>

    <template
      v-if="eventWithTxRef || assetMovementTransactionId || allTxRefs.length > 0"
      #txRef
    >
      <template v-if="assetMovementEvent && allTxRefs.length > 0">
        <HashLink
          :text="allTxRefs[0].txRef"
          type="transaction"
          :location="allTxRefs[0].location"
          :truncate-length="truncateLength"
          :reveal-actions="revealActions"
          show-location-icon
        />
        <RuiMenu
          v-if="extraHashCount > 0"
          v-model="hashMenuOpen"
          :options="{ placement: 'bottom-start' }"
        >
          <template #activator="{ attrs }">
            <RuiButton
              size="sm"
              variant="text"
              icon
              class="h-6! px-1.5! text-xs"
              v-bind="attrs"
            >
              {{ extraHashCount }}+
            </RuiButton>
          </template>
          <div class="flex flex-col gap-1 p-2">
            <HashLink
              v-for="(item, index) in allTxRefs.slice(1)"
              :key="index"
              class="bg-rui-grey-200 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full text-xs"
              :text="item.txRef"
              type="transaction"
              :location="item.location"
              :truncate-length="truncateLength"
              show-location-icon
            />
          </div>
        </RuiMenu>
      </template>

      <HashLink
        v-else-if="assetMovementEvent && assetMovementTransactionId"
        :text="assetMovementTransactionId"
        type="transaction"
        :location="assetMovementEvent?.extraData?.blockchain || undefined"
        :truncate-length="truncateLength"
        :display-mode="assetMovementEvent?.extraData?.blockchain ? 'default' : 'copy'"
        :reveal-actions="revealActions"
        show-location-icon
      />

      <HashLink
        v-else-if="eventWithTxRef"
        :text="eventWithTxRef.txRef"
        type="transaction"
        :location="eventWithTxRef.location"
        :truncate-length="truncateLength"
        :reveal-actions="revealActions"
      />
    </template>

    <template
      v-if="assetMovementEvent"
      #verb
    >
      {{
        assetMovementEvent.eventSubtype === 'spend'
          ? t('transactions.events.headers.asset_movement_event_withdraw')
          : t('transactions.events.headers.asset_movement_event_deposit')
      }}
    </template>
  </i18n-t>
</template>
