<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { Blockchain, HistoryEventEntryType, toSentenceCase, toSnakeCase } from '@rotki/common';
import HashLink from '@/modules/common/links/HashLink.vue';
import {
  isAssetMovementEventRef,
  isEthBlockEventRef,
  isWithdrawalEventRef,
} from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const { t } = useI18n({ useScope: 'global' });

const { event } = toRefs(props);

const { is2xlAndUp } = useBreakpoint();

const blockEvent = isEthBlockEventRef(event);
const withdrawEvent = isWithdrawalEventRef(event);
const assetMovementEvent = isAssetMovementEventRef(event);
const eventWithTxRef = computed<{ location: string; txRef: string } | undefined>(() => {
  const event = props.event;
  if ('txRef' in event && event.txRef) {
    return {
      location: event.location,
      txRef: event.txRef,
    };
  }
  return undefined;
});

const translationKey = computed<string>(() => {
  // consider an evm swap event as a case of evm event
  // as they are both evm events and have the same header
  const eventVal = get(event);
  let entryType = eventVal.entryType;
  const specialTypesWithTxRef: HistoryEventEntryType[] = [
    HistoryEventEntryType.ETH_DEPOSIT_EVENT,
    HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
  ];

  if (get(eventWithTxRef) && !specialTypesWithTxRef.includes(entryType)) {
    entryType = HistoryEventEntryType.EVM_EVENT;
  }

  return `transactions.events.headers.${toSnakeCase(entryType)}`;
});

const assetMovementTransactionId = computed<string | undefined>(() => get(assetMovementEvent)?.extraData?.transactionId ?? undefined);

/**
 * The key is used to avoid an issue where the block event identifier would be reused
 * to display a hash event identifier resulting in a numerical display instead.
 */
const key = computed(() => {
  if (get(eventWithTxRef))
    return 'tx_hash';
  else if (get(blockEvent))
    return 'block';
  else if (get(withdrawEvent))
    return 'withdraw';
  else if (get(assetMovementEvent))
    return 'asset_movement';
  else
    return undefined;
});
</script>

<template>
  <i18n-t
    :key="key"
    scope="global"
    :keypath="translationKey"
    tag="div"
    class="flex flex-wrap items-center gap-x-1.5 gap-y-1"
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
      v-if="eventWithTxRef || assetMovementTransactionId"
      #txRef
    >
      <HashLink
        v-if="eventWithTxRef"
        class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
        :text="eventWithTxRef.txRef"
        type="transaction"
        :location="eventWithTxRef.location"
        :truncate-length="is2xlAndUp ? 0 : 8"
      />
      <HashLink
        v-else-if="assetMovementTransactionId"
        class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 pl-2 rounded-full m-0.5"
        :text="assetMovementTransactionId"
        type="transaction"
        :location="assetMovementEvent?.extraData?.blockchain || undefined"
        :truncate-length="is2xlAndUp ? 0 : 8"
        :display-mode="assetMovementEvent?.extraData?.blockchain ? 'default' : 'copy'"
      />
    </template>

    <template
      v-if="assetMovementEvent"
      #verb
    >
      {{
        assetMovementEvent.eventType === 'withdrawal'
          ? t('transactions.events.headers.asset_movement_event_withdraw')
          : t('transactions.events.headers.asset_movement_event_deposit')
      }}
    </template>
  </i18n-t>
</template>
