<script setup lang="ts">
import { useTxQueryStatusStore } from '@/store/history/query-status';
import { type EthereumTransactionQueryData } from '@/types/websocket-messages';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import TransactionQueryStatusDialog from '@/components/history/transactions/query-status/TransactionQueryStatusDialog.vue';
import TransactionQueryStatusCurrent from '@/components/history/transactions/query-status/TransactionQueryStatusCurrent.vue';
import TransactionQueryStatusLine from '@/components/history/transactions/query-status/TransactionQueryStatusLine.vue';

defineProps<{ colspan: number }>();

const openStatusDropdown = ref<boolean>(false);

const store = useTxQueryStatusStore();
const { queryStatus, isAllFinished, length } = toRefs(store);

const { isStatusFinished, resetQueryStatus } = store;

const sortedQueryStatus = computed<EthereumTransactionQueryData[]>(() => {
  const statuses = Object.values(get(queryStatus));

  return statuses.sort(
    (a: EthereumTransactionQueryData, b: EthereumTransactionQueryData) =>
      (isStatusFinished(a) ? 1 : 0) - (isStatusFinished(b) ? 1 : 0)
  );
});

const css = useCssModule();
</script>
<template>
  <tr v-if="length > 0" :class="css.tr">
    <td :colspan="colspan" class="py-2">
      <div class="d-flex">
        <div v-if="isAllFinished" class="pr-2">
          <v-btn icon @click="resetQueryStatus">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </div>
        <div class="pr-2">
          <v-btn
            v-if="length > 1 && !isAllFinished"
            icon
            @click="openStatusDropdown = !openStatusDropdown"
          >
            <v-icon v-if="openStatusDropdown"> mdi-chevron-up </v-icon>
            <v-icon v-else> mdi-chevron-down </v-icon>
          </v-btn>
        </div>
        <div>
          <div
            v-if="isAllFinished || (!openStatusDropdown && length > 1)"
            class="py-2 d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isAllFinished"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>
            <transaction-query-status-current />
          </div>
          <div
            v-for="item in sortedQueryStatus"
            v-else
            :key="item.address + item.evmChain"
            class="d-flex align-center"
          >
            <div class="mr-4">
              <v-progress-circular
                v-if="!isStatusFinished(item)"
                size="20"
                color="primary"
                width="2"
                indeterminate
              />
              <v-icon v-else color="green" :class="css['check-icon']">
                mdi-check-circle
              </v-icon>
            </div>

            <evm-chain-icon :chain="item.evmChain" size="20px" />

            <transaction-query-status-line :item="item" class="ms-2" />
          </div>
        </div>
        <v-spacer />
        <transaction-query-status-dialog />
      </div>
    </td>
  </tr>
</template>
<style module lang="scss">
.tr {
  background: transparent !important;
}

.row {
  display: flex;
}

.check-icon {
  margin: -2px;
}
</style>
