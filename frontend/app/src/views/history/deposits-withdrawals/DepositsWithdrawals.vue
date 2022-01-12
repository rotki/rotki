<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('deposits_withdrawals.loading') }}
    </template>
    {{ $t('deposits_withdrawals.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <deposits-withdrawals-content class="mt-8" @fetch="fetchAssetMovements" />
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount } from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useAssetMovements } from '@/store/history';
import DepositsWithdrawalsContent from '@/views/history/deposits-withdrawals/DepositsWithdrawalsContent.vue';

export default defineComponent({
  name: 'DepositsWithdrawals',
  components: {
    DepositsWithdrawalsContent,
    ProgressScreen
  },
  setup() {
    const { fetchAssetMovements } = useAssetMovements();

    onBeforeMount(async () => {
      await fetchAssetMovements();
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchAssetMovements,
      loading: shouldShowLoadingScreen(Section.ASSET_MOVEMENT)
    };
  }
});
</script>
