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
  groupEvents?: HistoryEventEntry[];
}>();

const { t } = useI18n({ useScope: 'global' });

const { event } = toRefs(props);

const { is2xlAndUp, isMd } = useBreakpoint();

const truncateLength = computed<number>(() => {
  if (get(is2xlAndUp)) {
    return 12;
  }

  if (get(isMd)) {
    return 6;
  }

  return 8;
});

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

const allTxRefs = computed<{ location: string; txRef: string }[]>(() => {
  if (!get(assetMovementEvent) || !props.groupEvents)
    return [];

  const seen = new Set<string>();
  const result: { location: string; txRef: string }[] = [];

  for (const child of props.groupEvents) {
    if (!('txRef' in child) || !child.txRef || seen.has(child.txRef))
      continue;

    seen.add(child.txRef);
    result.push({
      location: child.location,
      txRef: child.txRef,
    });
  }

  return result;
});

const extraHashCount = computed<number>(() => Math.max(get(allTxRefs).length - 1, 0));

const hashMenuOpen = ref<boolean>(false);

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
          :popper="{ placement: 'bottom-start' }"
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
