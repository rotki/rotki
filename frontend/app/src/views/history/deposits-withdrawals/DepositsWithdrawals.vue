<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('deposits_withdrawals.loading') }}
    </template>
    {{ $t('deposits_withdrawals.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <deposits-withdrawals-content
      class="mt-8"
      @fetch="fetchMovementsHandler"
      @update:payload="onFilterUpdate($event)"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount, ref } from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import {
  setupAssetMovements,
  setupAssociatedLocations
} from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import { AssetMovementRequestPayload } from '@/services/history/types';
import { Section } from '@/store/const';
import DepositsWithdrawalsContent from '@/views/history/deposits-withdrawals/DepositsWithdrawalsContent.vue';

export default defineComponent({
  name: 'DepositsWithdrawals',
  components: {
    DepositsWithdrawalsContent,
    ProgressScreen
  },
  setup() {
    const { itemsPerPage } = setupSettings();
    const { fetchAssetMovements } = setupAssetMovements();
    const { fetchAssociatedLocations } = setupAssociatedLocations();

    const payload = ref<AssetMovementRequestPayload>({
      limit: itemsPerPage.value,
      offset: 0,
      orderByAttribute: 'time',
      ascending: false
    });

    const fetchMovementsHandler = async (refresh: boolean = false) => {
      await fetchAssetMovements({
        ...payload.value,
        onlyCache: !refresh
      });
    };

    const onFilterUpdate = (newPayload: AssetMovementRequestPayload) => {
      payload.value = newPayload;
      fetchMovementsHandler().then();
    };

    onBeforeMount(async () => {
      fetchAssociatedLocations().then();
      fetchMovementsHandler().then();
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchMovementsHandler,
      onFilterUpdate,
      loading: shouldShowLoadingScreen(Section.ASSET_MOVEMENT)
    };
  }
});
</script>
