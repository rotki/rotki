<template>
  <div>
    <v-row>
      <v-col>
        <refresh-header
          :loading="refreshing"
          title="Defi Overview"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <progress-screen v-if="loading">
      <template #message>
        Please wait while your defi balances are getting loaded...
      </template>
    </progress-screen>
    <v-row>
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
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import InfoRow from '@/components/defi/display/InfoRow.vue';
import Overview from '@/components/defi/Overview.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { Status } from '@/store/defi/status';
import { DefiProtocolSummary } from '@/store/defi/types';

@Component({
  components: {
    ProgressScreen,
    Overview,
    RefreshHeader,
    InfoRow,
    StatCard,
    AmountDisplay
  },
  computed: {
    ...mapState('defi', ['status', 'defiStatus']),
    ...mapGetters('defi', ['defiOverview'])
  },
  methods: {
    ...mapActions('defi', ['fetchAllDefi'])
  }
})
export default class DecentralizedOverview extends Vue {
  status!: Status;
  defiStatus!: Status;
  fetchAllDefi!: (refresh: boolean) => Promise<void>;
  defiOverview!: DefiProtocolSummary[];

  get refreshing(): boolean {
    return this.status !== Status.LOADED;
  }

  get loading(): boolean {
    return (
      this.defiStatus !== Status.LOADED && this.defiStatus !== Status.REFRESHING
    );
  }

  async refresh() {
    await this.fetchAllDefi(true);
  }

  async created() {
    await this.fetchAllDefi(false);
  }
}
</script>

<style scoped></style>
