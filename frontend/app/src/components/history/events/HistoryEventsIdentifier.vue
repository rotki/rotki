<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type HistoryEventEntry } from '@/types/history/events';
import { toSentenceCase, toSnakeCase } from '@/utils/text';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const { event } = toRefs(props);

const translationKey: ComputedRef<string> = computed(
  () => `transactions.events.headers.${toSnakeCase(get(event).entryType)}`
);

const { getChain } = useSupportedChains();

const evmOrDepositEvent = computed(
  () => get(isEvmEventRef(event)) || get(isEthDepositEventRef(event))
);
const blockEvent = isEthBlockEventRef(event);
const withdrawEvent = isWithdrawalEventRef(event);

const css = useCssModule();
const { xl } = useDisplay();
</script>

<template>
  <i18n :path="translationKey" tag="span" class="flex items-center gap-2">
    <template #location>
      {{ toSentenceCase(event.location) }}
    </template>

    <template v-if="blockEvent" #blockNumber>
      <HashLink
        :class="css['address__content']"
        :text="blockEvent.blockNumber.toString()"
        :show-icon="false"
        type="block"
      />
    </template>

    <template v-if="withdrawEvent" #validatorIndex>
      <HashLink
        :class="css['address__content']"
        :text="withdrawEvent.validatorIndex.toString()"
        :show-icon="false"
        :chain="Blockchain.ETH2"
        type="address"
      />
    </template>

    <template v-if="evmOrDepositEvent" #txHash>
      <HashLink
        :class="css['address__content']"
        :text="evmOrDepositEvent.txHash"
        :show-icon="false"
        type="transaction"
        :chain="getChain(evmOrDepositEvent.location)"
        :truncate-length="8"
        :full-address="xl"
      />
    </template>
  </i18n>
</template>

<style lang="scss" module>
.address {
  &__content {
    background: var(--v-rotki-light-grey-darken1);
    padding: 0.125rem 0.25rem 0.125rem 0.5rem;
    border-radius: 3rem;
    margin: 2px;
  }
}
</style>
