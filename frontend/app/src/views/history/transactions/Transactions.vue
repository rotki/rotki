<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('transactions.loading') }}
    </template>
    {{ $t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <transaction-content
      @fetch="fetchTransactionsHandler"
      @update:payload="onFilterUpdate($event)"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount, ref } from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import { setupTransactions } from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import { TransactionRequestPayload } from '@/services/history/types';
import { Section } from '@/store/const';
import TransactionContent from '@/views/history/transactions/TransactionContent.vue';

export default defineComponent({
  name: 'Transactions',
  components: {
    ProgressScreen,
    TransactionContent
  },
  setup() {
    const { itemsPerPage } = setupSettings();

    const { fetchTransactions } = setupTransactions();

    const payload = ref<TransactionRequestPayload>({
      limit: itemsPerPage.value,
      offset: 0,
      orderByAttribute: 'timestamp',
      ascending: false
    });

    const fetchTransactionsHandler = async (refresh: boolean = false) => {
      await fetchTransactions({
        ...payload.value,
        onlyCache: !refresh
      });
    };

    const onFilterUpdate = (newPayload: TransactionRequestPayload) => {
      payload.value = newPayload;
      fetchTransactionsHandler().then();
    };

    onBeforeMount(async () => {
      fetchTransactionsHandler().then();
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchTransactionsHandler,
      onFilterUpdate,
      loading: shouldShowLoadingScreen(Section.TX)
    };
  }
});
</script>
