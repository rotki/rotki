<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ t('deposits_withdrawals.loading') }}
    </template>
    {{ t('deposits_withdrawals.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <deposits-withdrawals-content class="mt-8" @fetch="fetchAssetMovements" />
  </div>
</template>

<script setup lang="ts">
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import DepositsWithdrawalsContent from '@/components/history/deposits-withdrawals/DepositsWithdrawalsContent.vue';
import { useSectionLoading } from '@/composables/common';
import { useAssetMovements } from '@/store/history/asset-movements';
import { Section } from '@/types/status';

const { fetchAssetMovements } = useAssetMovements();

onBeforeMount(async () => {
  await fetchAssetMovements();
});

const { shouldShowLoadingScreen } = useSectionLoading();
const loading = shouldShowLoadingScreen(Section.ASSET_MOVEMENT);

const { t } = useI18n();
</script>
