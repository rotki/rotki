<script setup lang="ts">
import { useTransactions } from '@/store/history/transactions';
import { Section } from '@/types/status';

const ProgressScreen = defineAsyncComponent(
  () => import('@/components/helper/ProgressScreen.vue')
);
const TransactionContent = defineAsyncComponent(
  () => import('@/components/history/transactions/TransactionContent.vue')
);
const { fetchTransactions } = useTransactions();

const { shouldShowLoadingScreen } = useSectionLoading();
const loading = shouldShowLoadingScreen(Section.TX);

const { t } = useI18n();

onBeforeMount(async () => {
  await fetchTransactions();
});
</script>

<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ t('transactions.loading') }}
    </template>
    {{ t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <transaction-content />
  </div>
</template>
