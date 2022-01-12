<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('transactions.loading') }}
    </template>
    {{ $t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <transaction-content @fetch="fetchTransactions" />
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount } from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useTransactions } from '@/store/history';
import TransactionContent from '@/views/history/transactions/TransactionContent.vue';

export default defineComponent({
  name: 'Transactions',
  components: {
    ProgressScreen,
    TransactionContent
  },
  setup() {
    const { fetchTransactions } = useTransactions();

    onBeforeMount(async () => {
      await fetchTransactions();
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchTransactions,
      loading: shouldShowLoadingScreen(Section.TX)
    };
  }
});
</script>
