<script setup lang="ts">
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import LedgerActionContent from '@/components/history/ledger-actions/LedgerActionContent.vue';
import { Section } from '@/types/status';
import { type LocationQuery } from '@/types/route';

const { fetchLedgerActions } = useLedgerActionStore();

onBeforeMount(async () => {
  await fetchLedgerActions();
});

const { shouldShowLoadingScreen } = useSectionLoading();
const loading = shouldShowLoadingScreen(Section.LEDGER_ACTIONS);

const { t } = useI18n();

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
      {{ t('ledger_actions.loading') }}
    </template>
    {{ t('ledger_actions.loading_subtitle') }}
  </progress-screen>
  <div v-else class="mt-8">
    <ledger-action-content
      read-filter-from-route
      @fetch="fetchLedgerActions"
      @update:query-params="redirect($event)"
    />
  </div>
</template>
