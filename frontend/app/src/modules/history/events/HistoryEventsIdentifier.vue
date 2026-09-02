<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { Blockchain, toSentenceCase } from '@rotki/common';
import { useHistoryEventsIdentifier } from '@/modules/history/events/use-history-events-identifier';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { event, groupEvents } = defineProps<{
  event: HistoryEventEntry;
  groupEvents?: HistoryEventEntry[];
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
      {{ toSentenceCase(event.location) }}
    </template>

    <template
      v-if="blockEvent"
      #blockNumber
    >
      <HashLink
        class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
        :text="blockEvent.blockNumber.toString()"
        type="block"
      />
    </template>

    <template
      v-if="withdrawEvent"
      #validatorIndex
    >
      <HashLink
        class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
        :text="withdrawEvent.validatorIndex.toString()"
        :location="Blockchain.ETH2"
      />
    </template>

    <template
      v-if="eventWithTxRef || assetMovementTransactionId || allTxRefs.length > 0"
      #txRef
    >
      <!-- Asset movement: show all tx hashes with location icon -->
      <template v-if="assetMovementEvent && allTxRefs.length > 0">
        <HashLink
          class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
          :text="allTxRefs[0].txRef"
          type="transaction"
          :location="allTxRefs[0].location"
          :truncate-length="truncateLength"
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
              icon
              class="-ml-1 !h-6 !px-2 text-xs !bg-rui-grey-300 hover:!bg-rui-grey-400 dark:!bg-rui-grey-800 hover:dark:!bg-rui-grey-700 dark:!text-white"
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

      <!-- Asset movement fallback: transactionId from extraData -->
      <HashLink
        v-else-if="assetMovementEvent && assetMovementTransactionId"
        class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
        :text="assetMovementTransactionId"
        type="transaction"
        :location="assetMovementEvent?.extraData?.blockchain || undefined"
        :truncate-length="truncateLength"
        :display-mode="assetMovementEvent?.extraData?.blockchain ? 'default' : 'copy'"
        show-location-icon
      />

      <!-- Non-asset-movement: show single hash as before -->
      <HashLink
        v-else-if="eventWithTxRef"
        class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
        :text="eventWithTxRef.txRef"
        type="transaction"
        :location="eventWithTxRef.location"
        :truncate-length="truncateLength"
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
