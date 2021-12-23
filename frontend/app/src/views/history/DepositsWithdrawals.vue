<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('deposits_withdrawals.loading') }}
    </template>
    {{ $t('deposits_withdrawals.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <deposits-withdrawals-content
      :items="assetMovements"
      :total="assetMovementsTotal"
      :limit="assetMovementsLimit"
      :refreshing="refreshing"
      :loading="loading"
      @refresh="refresh"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { mapActions, mapGetters } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import {
  FETCH_FROM_SOURCE,
  FETCH_REFRESH,
  HistoryActions
} from '@/store/history/consts';
import { FetchSource } from '@/store/history/types';
import DepositsWithdrawalsContent from '@/views/history/DepositsWithdrawalsContent.vue';

export default defineComponent({
  name: 'DepositsWithdrawals',
  components: {
    DepositsWithdrawalsContent,
    ProgressScreen
  },
  mixins: [StatusMixin],
  data() {
    return {
      section: Section.ASSET_MOVEMENT
    };
  },
  computed: {
    ...mapGetters('history', [
      'assetMovements',
      'assetMovementsTotal',
      'assetMovementsLimit'
    ])
  },
  async created() {
    const { fetchAssociatedLocations } = this as {
      fetchAssociatedLocations: () => Promise<void>;
    };

    await fetchAssociatedLocations();
    await this.fetch(FETCH_FROM_SOURCE);
  },
  methods: {
    ...mapActions('history', [
      HistoryActions.FETCH_MOVEMENTS,
      HistoryActions.FETCH_ASSOCIATED_LOCATIONS
    ]),

    async refresh() {
      await this.fetch(FETCH_REFRESH);
    },

    async fetch(source: FetchSource) {
      const { fetchMovements } = this as {
        fetchMovements: (source: FetchSource) => Promise<void>;
      };
      await fetchMovements(source);
    }
  }
});
</script>
