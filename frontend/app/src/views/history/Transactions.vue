<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('transactions.loading') }}
    </template>
    {{ $t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <card class="mt-8" outlined-body>
      <template #title>
        <refresh-button
          :loading="refreshing"
          :tooltip="$t('transactions.refresh_tooltip')"
          @refresh="refresh"
        />
        {{ $t('transactions.title') }}
        <v-icon v-if="loading || refreshing" color="primary" class="ml-2">
          mdi-spin mdi-loading
        </v-icon>
      </template>
      <template #actions>
        <v-row no-gutters>
          <v-col cols="12" md="6">
            <ignore-buttons
              :disabled="selected.length === 0 || loading || refreshing"
              @ignore="ignore"
            />
          </v-col>
          <v-col cols="12" md="6" lg="4" offset-lg="2">
            <blockchain-account-selector
              v-model="account"
              :chains="['ETH']"
              dense
              :label="$t('transactions.filter.label')"
              outlined
              no-padding
              flat
            />
          </v-col>
        </v-row>
      </template>
      <transaction-table
        :transactions="transactions"
        :limit="limit"
        :total="total"
        :found="found"
        :selected="selected"
        :is-selected="isSelected"
        @update:selection="selectionChanged(...$event)"
        @update:pagination="onPaginationUpdate($event)"
      />
    </card>
  </div>
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import {
  defineComponent,
  onBeforeMount,
  Ref,
  ref,
  watch
} from '@vue/composition-api';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import { setupStatusChecking } from '@/composables/common';
import { setupTransactions } from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import {
  EthTransaction,
  TransactionRequestPayload
} from '@/services/history/types';
import { Section } from '@/store/const';
import { EthTransactionEntry, IgnoreActionType } from '@/store/history/types';
import { setupIgnore } from '@/views/history/composables/ignore';
import { setupSelectionMode } from '@/views/history/composables/selection';
import TransactionTable from '@/views/history/tx/TransactionTable.vue';

export default defineComponent({
  name: 'Transactions',
  components: {
    TransactionTable,
    IgnoreButtons,
    BlockchainAccountSelector,
    RefreshButton,
    ProgressScreen
  },
  setup() {
    const account: Ref<GeneralAccount | null> = ref(null);
    const { itemsPerPage } = setupSettings();

    const payload = ref<TransactionRequestPayload>({
      limit: itemsPerPage.value,
      offset: 0,
      orderByAttribute: 'timestamp',
      ascending: false
    });

    watch(account, account => {
      const limit = itemsPerPage.value;
      payload.value = {
        ...payload.value,
        offset: 0,
        limit,
        address: account?.address
      };
      fetchTransactionsHandler().then();
    });

    const { transactions, limit, found, total, fetchTransactions } =
      setupTransactions();

    const fetchTransactionsHandler = async (refresh: boolean = false) => {
      await fetchTransactions({
        ...payload.value,
        onlyCache: !refresh
      });
    };

    const refresh = async () => await fetchTransactionsHandler(true);

    const onPaginationUpdate = ({
      ascending,
      page,
      sortBy,
      itemsPerPage
    }: {
      page: number;
      itemsPerPage: number;
      sortBy: keyof EthTransaction;
      ascending: boolean;
    }) => {
      const offset = (page - 1) * itemsPerPage;
      payload.value = {
        ...payload.value,
        orderByAttribute: sortBy,
        offset,
        limit: itemsPerPage,
        ascending
      };

      fetchTransactionsHandler().then();
    };

    onBeforeMount(async () => await fetchTransactionsHandler());

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const { selected, isSelected, selectionChanged } =
      setupSelectionMode<EthTransactionEntry>(
        transactions,
        item => item.identifier
      );

    return {
      account,
      transactions,
      limit,
      total,
      found,
      loading: shouldShowLoadingScreen(Section.TX),
      refreshing: isSectionRefreshing(Section.TX),
      refresh,
      selected,
      isSelected,
      selectionChanged,
      fetchTransactionsHandler,
      onPaginationUpdate,
      ...setupIgnore(
        IgnoreActionType.ETH_TRANSACTIONS,
        selected,
        transactions,
        () => fetchTransactionsHandler(false),
        item => item.identifier
      )
    };
  }
});
</script>
