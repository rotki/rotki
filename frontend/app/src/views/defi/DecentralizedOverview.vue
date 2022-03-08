<template>
  <div>
    <v-row class="mt-6">
      <v-col>
        <refresh-header
          :loading="refreshing"
          :title="$t('decentralized_overview.title')"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <progress-screen v-if="loading">
      <template #message>{{ $t('decentralized_overview.loading') }}</template>
    </progress-screen>
    <no-data-screen
      v-else-if="defiOverview.length === 0"
      :full="false"
      class="mt-16"
    >
      <template #title>
        {{ $t('decentralized_overview.empty_title') }}
      </template>
      <span class="text-subtitle-2 text--secondary">
        {{ $t('decentralized_overview.empty_subtitle') }}
      </span>
    </no-data-screen>
    <v-row class="mt-4">
      <v-col
        v-for="summary in defiOverview"
        :key="summary.protocol.name"
        lg="6"
        xl="3"
      >
        <overview :summary="summary" />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import NoDataScreen from '@/components/common/NoDataScreen.vue';
import Overview from '@/components/defi/Overview.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { DefiProtocolSummary } from '@/store/defi/types';

@Component({
  components: {
    NoDataScreen,
    ProgressScreen,
    Overview,
    RefreshHeader
  },
  computed: {
    ...mapGetters('defi', ['defiOverview'])
  },
  methods: {
    ...mapActions('defi', ['fetchAllDefi'])
  }
})
export default class DecentralizedOverview extends Mixins(StatusMixin) {
  fetchAllDefi!: (refresh: boolean) => Promise<void>;
  defiOverview!: DefiProtocolSummary[];
  section = Section.DEFI_OVERVIEW;

  async refresh() {
    await this.fetchAllDefi(true);
  }

  async created() {
    await this.fetchAllDefi(false);
  }
}
</script>
