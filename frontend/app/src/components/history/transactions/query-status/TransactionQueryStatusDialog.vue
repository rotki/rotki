<script setup lang="ts">
import { useTxQueryStatusStore } from '@/store/history/query-status';
import TransactionQueryStatusCurrent from '@/components/history/transactions/query-status/TransactionQueryStatusCurrent.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import TransactionQueryStatusLine from '@/components/history/transactions/query-status/TransactionQueryStatusLine.vue';
import TransactionQueryStatusSteps from '@/components/history/transactions/query-status/TransactionQueryStatusSteps.vue';

const { t } = useI18n();
const css = useCssModule();

const { queryStatus } = toRefs(useTxQueryStatusStore());
</script>

<template>
  <v-dialog width="1200">
    <template #activator="{ on }">
      <v-btn text class="ml-4" v-on="on">
        {{ t('common.details') }}
        <v-icon small>mdi-chevron-right</v-icon>
      </v-btn>
    </template>
    <template #default="dialog">
      <v-card :class="$style.card">
        <v-card-title class="d-flex justify-space-between pb-0">
          <div>
            {{ t('transactions.query_status.title') }}
          </div>
          <v-btn icon @click="dialog.value = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <transaction-query-status-current class="px-6 pb-4 text-caption" />

        <div class="px-6 pb-4">
          <div
            v-for="item in queryStatus"
            :key="item.address + item.evmChain"
            :class="css.item"
          >
            <div class="d-flex align-center">
              <evm-chain-icon :chain="item.evmChain" size="20px" />

              <transaction-query-status-line :item="item" class="ms-2" />

              <v-tooltip bottom>
                <template #activator="{ on }">
                  <v-icon class="ml-2" v-on="on"> mdi-help-circle </v-icon>
                </template>
                <i18n
                  :path="
                    item.period[0] === 0
                      ? 'transactions.query_status.latest_period_end_date'
                      : 'transactions.query_status.latest_period_date_range'
                  "
                >
                  <template #start>
                    <date-display :timestamp="item.period[0]" />
                  </template>
                  <template #end>
                    <date-display :timestamp="item.period[1]" />
                  </template>
                </i18n>
              </v-tooltip>
            </div>
            <transaction-query-status-steps :item="item" />
          </div>
        </div>
      </v-card>
    </template>
  </v-dialog>
</template>

<style module lang="scss">
.item {
  padding: 1rem 0;
  border-top: 1px solid var(--v-rotki-light-grey-darken1);
}

.card {
  width: 100%;
  overflow: auto;
}
</style>
