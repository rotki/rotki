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
        @update:selected="selected = $event"
        @update:pagination="onPaginationUpdate($event)"
      />
    </card>
  </div>
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import {
  computed,
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
import {
  EthTransaction,
  TransactionRequestPayload
} from '@/services/history/types';
import { Section } from '@/store/const';
import { HistoryActions } from '@/store/history/consts';
import { IgnoreActionType } from '@/store/history/types';
import { getKey } from '@/store/history/utils';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { setupIgnore } from '@/views/history/composables/ignore';
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
    const selected: Ref<string[]> = ref([]);
    const store = useStore();

    const state: RotkehlchenState = store.state;
    const itemsPerPage = state.settings!!.itemsPerPage;

    const payload = ref<TransactionRequestPayload>({
      limit: itemsPerPage,
      offset: 0,
      orderByAttribute: 'timestamp',
      ascending: false
    });

    watch(account, account => {
      const state: RotkehlchenState = store.state;
      const limit = state.settings!!.itemsPerPage;
      payload.value = {
        ...payload.value,
        offset: 0,
        limit,
        address: account?.address
      };
      fetchTransactions().then();
    });

    const transactions = computed(() => {
      const state: RotkehlchenState = store.state;
      return state.history!!.transactions.entries;
    });
    const limit = computed(() => {
      const state: RotkehlchenState = store.state;
      return state.history!!.transactions.entriesLimit;
    });
    const found = computed(() => {
      const state: RotkehlchenState = store.state;
      return state.history!!.transactions.entriesFound;
    });
    const total = computed(() => {
      const state: RotkehlchenState = store.state;
      return state.history!!.transactions.entriesTotal;
    });

    const fetchTransactions = async (refresh: boolean = false) => {
      await store.dispatch(`history/${HistoryActions.FETCH_TRANSACTIONS}`, {
        ...payload.value,
        onlyCache: !refresh
      });
    };

    const refresh = async () => await fetchTransactions(true);

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

      fetchTransactions().then();
    };

    onBeforeMount(async () => await fetchTransactions());

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

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
      fetchTransactions,
      onPaginationUpdate,
      ...setupIgnore(
        IgnoreActionType.ETH_TRANSACTIONS,
        selected,
        transactions,
        item => getKey(item.entry)
      )
    };
  }
});
</script>
