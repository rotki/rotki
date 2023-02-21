<script setup lang="ts">
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import DepositsWithdrawalsContent from '@/components/history/deposits-withdrawals/DepositsWithdrawalsContent.vue';
import { Section } from '@/types/status';
import { type LocationQuery } from '@/types/route';

const { fetchAssetMovements } = useAssetMovements();

onBeforeMount(async () => {
  await fetchAssetMovements();
});

const { shouldShowLoadingScreen } = useSectionLoading();
const loading = shouldShowLoadingScreen(Section.ASSET_MOVEMENT);

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
      {{ t('deposits_withdrawals.loading') }}
    </template>
    {{ t('deposits_withdrawals.loading_subtitle') }}
  </progress-screen>
  <div v-else class="mt-8">
    <deposits-withdrawals-content
      read-filter-from-route
      @fetch="fetchAssetMovements"
      @update:query-params="redirect($event)"
    />
  </div>
</template>
