<template>
  <div>
    <v-row>
      <v-col>
        <refresh-header
          :loading="loading"
          title="Defi Overview"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col v-for="summary in defiOverview" :key="summary.protocol">
        <overview
          :title="summary.protocol"
          :loading="loading"
          :summary="summary"
        />
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
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { Status } from '@/store/defi/status';
import { DefiProtocolSummary } from '@/store/defi/types';

@Component({
  components: { Overview, RefreshHeader, InfoRow, StatCard, AmountDisplay },
  computed: {
    ...mapState('defi', ['status']),
    ...mapGetters('defi', ['defiOverview'])
  },
  methods: {
    ...mapActions('defi', ['fetchAllDefi'])
  }
})
export default class DecentralizedOverview extends Vue {
  status!: Status;
  fetchAllDefi!: (refresh: boolean) => Promise<void>;
  defiOverview!: DefiProtocolSummary[];

  get loading(): boolean {
    return this.status !== Status.LOADED;
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
