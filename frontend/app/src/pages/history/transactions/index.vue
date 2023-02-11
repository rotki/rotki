<script setup lang="ts">
import { Section } from '@/types/status';
import { type LocationQuery } from '@/types/route';

const ProgressScreen = defineAsyncComponent(
  () => import('@/components/helper/ProgressScreen.vue')
);
const TransactionContent = defineAsyncComponent(
  () => import('@/components/history/transactions/TransactionContent.vue')
);
const { fetchTransactions } = useTransactionStore();

const { shouldShowLoadingScreen } = useSectionLoading();
const loading = shouldShowLoadingScreen(Section.TX);

const { t } = useI18n();

onBeforeMount(async () => {
  await fetchTransactions();
});

const router = useRouter();
const redirect = async (query: LocationQuery) => {
  await router.push({
    query,
    replace: true
  });
};
</script>

<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ t('transactions.loading') }}
    </template>
    {{ t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <transaction-content
      read-filter-from-route
      @update:query-params="redirect($event)"
    />
  </div>
</template>
