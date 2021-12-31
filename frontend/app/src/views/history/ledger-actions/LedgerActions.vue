<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('ledger_actions.loading') }}
    </template>
    {{ $t('ledger_actions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <div class="mt-8">
      <ledger-action-content
        @fetch="fetchLedgerActionsHandler"
        @update:payload="onFilterUpdate($event)"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount, ref } from '@vue/composition-api';
import isEqual from 'lodash/isEqual';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import {
  setupAssociatedLocations,
  setupLedgerActions
} from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import { LedgerActionRequestPayload } from '@/services/history/types';
import { Section } from '@/store/const';
import LedgerActionContent from '@/views/history/ledger-actions/LedgerActionContent.vue';

export default defineComponent({
  name: 'LedgerActions',
  components: {
    ProgressScreen,
    LedgerActionContent
  },
  setup() {
    const { itemsPerPage } = setupSettings();
    const { fetchLedgerActions } = setupLedgerActions();
    const { fetchAssociatedLocations } = setupAssociatedLocations();

    const payload = ref<LedgerActionRequestPayload>({
      limit: itemsPerPage.value,
      offset: 0,
      orderByAttribute: 'timestamp',
      ascending: false
    });

    const fetchLedgerActionsHandler = async (refresh: boolean = false) => {
      if (refresh) {
        fetchAssociatedLocations().then();
      }
      await fetchLedgerActions({
        ...payload.value,
        onlyCache: !refresh
      });
    };

    const onFilterUpdate = (newPayload: LedgerActionRequestPayload) => {
      if (!isEqual(payload.value, newPayload)) {
        payload.value = newPayload;
        fetchLedgerActionsHandler().then();
      }
    };

    onBeforeMount(async () => {
      fetchAssociatedLocations().then();
      await fetchLedgerActionsHandler();
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchLedgerActionsHandler,
      onFilterUpdate,
      loading: shouldShowLoadingScreen(Section.LEDGER_ACTIONS)
    };
  }
});
</script>
