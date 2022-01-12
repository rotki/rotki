<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('ledger_actions.loading') }}
    </template>
    {{ $t('ledger_actions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <div class="mt-8">
      <ledger-action-content @fetch="fetchLedgerActions" />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, onBeforeMount } from '@vue/composition-api';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useLedgerActions } from '@/store/history';
import LedgerActionContent from '@/views/history/ledger-actions/LedgerActionContent.vue';

export default defineComponent({
  name: 'LedgerActions',
  components: {
    ProgressScreen,
    LedgerActionContent
  },
  setup() {
    const { fetchLedgerActions } = useLedgerActions();

    onBeforeMount(async () => {
      await fetchLedgerActions();
    });

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchLedgerActions,
      loading: shouldShowLoadingScreen(Section.LEDGER_ACTIONS)
    };
  }
});
</script>
