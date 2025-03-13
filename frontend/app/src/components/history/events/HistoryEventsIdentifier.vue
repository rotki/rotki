<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events';
import HashLink from '@/modules/common/links/HashLink.vue';
import {
  isAssetMovementEventRef,
  isEthBlockEventRef,
  isEthDepositEventRef,
  isEvmEventRef,
  isWithdrawalEventRef,
} from '@/utils/history/events';
import { Blockchain, toSentenceCase, toSnakeCase } from '@rotki/common';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const { t } = useI18n();

const { event } = toRefs(props);

const { is2xlAndUp } = useBreakpoint();

const translationKey = computed<string>(() => `transactions.events.headers.${toSnakeCase(get(event).entryType)}`);

const evmOrDepositEvent = computed(() => get(isEvmEventRef(event)) || get(isEthDepositEventRef(event)));
const blockEvent = isEthBlockEventRef(event);
const withdrawEvent = isWithdrawalEventRef(event);
const assetMovementEvent = isAssetMovementEventRef(event);

const assetMovementTransactionId = computed<string | undefined>(() => get(assetMovementEvent)?.extraData?.transactionId ?? undefined);

/**
 * The key is used to avoid an issue where the block event identifier would be reused
 * to display a hash event identifier resulting in a numerical display instead.
 */
const key = computed(() => {
  if (get(evmOrDepositEvent))
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
        :class="$style.wrapper"
        :text="blockEvent.blockNumber.toString()"
        type="block"
      />
    </template>

    <template
      v-if="withdrawEvent"
      #validatorIndex
    >
      <HashLink
        :class="$style.wrapper"
        :text="withdrawEvent.validatorIndex.toString()"
        :location="Blockchain.ETH2"
      />
    </template>

    <template
      v-if="evmOrDepositEvent || assetMovementTransactionId"
      #txHash
    >
      <HashLink
        v-if="evmOrDepositEvent"
        :class="$style.wrapper"
        :text="evmOrDepositEvent.txHash"
        type="transaction"
        :location="evmOrDepositEvent.location"
        :truncate-length="is2xlAndUp ? 0 : 8"
      />
      <HashLink
        v-else-if="assetMovementTransactionId"
        :class="$style.wrapper"
        :text="assetMovementTransactionId"
        type="transaction"
        :truncate-length="is2xlAndUp ? 0 : 8"
        display-mode="copy"
        hide-text
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

<style lang="scss" module>
.wrapper {
  @apply bg-rui-grey-300 pr-1 pl-2 rounded-full m-0.5;
}

:global(.dark) {
  .wrapper {
    @apply bg-rui-grey-800;
  }
}
</style>
