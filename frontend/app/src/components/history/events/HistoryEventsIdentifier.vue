<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type HistoryEventEntry } from '@/types/history/events';
import { toSentenceCase } from '@/utils/text';
import {
  isEthBlockEventRef,
  isEthDepositEventRef,
  isEvmEventRef,
  isWithdrawalEventRef
} from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const { event } = toRefs(props);

const translationKey: ComputedRef<string> = computed(
  () => `transactions.events.headers.${get(event).entryType.replace(/ /g, '_')}`
);

const { getChain } = useSupportedChains();

const evmOrDepositEvent = computed(
  () => get(isEvmEventRef(event)) || get(isEthDepositEventRef(event))
);
const blockEvent = isEthBlockEventRef(event);
const withdrawEvent = isWithdrawalEventRef(event);

const { currentBreakpoint } = useTheme();
const css = useCssModule();
</script>

<template>
  <div>
    <i18n :path="translationKey" tag="span" class="d-flex align-center">
      <template #location>
        {{ toSentenceCase(event.location) }}
      </template>

      <template #blockNumber>
        <span v-if="blockEvent" :class="css.address" class="d-inline-flex">
          <hash-link
            :class="css['address__content']"
            :text="blockEvent.blockNumber.toString()"
            :show-icon="false"
            type="block"
          />
        </span>
      </template>

      <template #validatorIndex>
        <span v-if="withdrawEvent" :class="css.address">
          <hash-link
            :class="css['address__content']"
            :text="withdrawEvent.validatorIndex.toString()"
            :show-icon="false"
            :chain="Blockchain.ETH2"
            type="address"
          />
        </span>
      </template>

      <template #txHash>
        <span v-if="evmOrDepositEvent" :class="css.address">
          <hash-link
            :class="css['address__content']"
            :text="evmOrDepositEvent.txHash"
            :show-icon="false"
            type="transaction"
            :chain="getChain(evmOrDepositEvent.location)"
            :truncate-length="8"
            :full-address="currentBreakpoint.xlOnly"
          />
        </span>
      </template>
    </i18n>
  </div>
</template>

<style lang="scss" module>
.address {
  vertical-align: middle;
  padding: 0 0.25rem;

  &__content {
    background: var(--v-rotki-light-grey-darken1);
    padding: 0.125rem 0.25rem 0.125rem 0.5rem;
    border-radius: 3rem;
    margin: 2px;
  }
}
</style>
