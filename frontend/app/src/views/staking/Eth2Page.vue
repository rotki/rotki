<template>
  <v-container>
    <progress-screen v-if="loading">
      <template #message>
        {{ $t('eth2page.loading') }}
      </template>
    </progress-screen>
    <eth2-staking
      v-else
      :refreshing="refreshing"
      :secondary-refreshing="secondaryRefreshing"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';

import { mapActions } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Eth2Staking } from '@/premium/premium';
import { Section } from '@/store/const';

@Component({
  components: { ProgressScreen, Eth2Staking },
  methods: {
    ...mapActions('staking', ['fetchStakingDetails'])
  }
})
export default class Eth2Page extends Mixins(StatusMixin) {
  readonly section = Section.STAKING_ETH2;
  readonly secondSection = Section.STAKING_ETH2_DEPOSITS;
  fetchStakingDetails!: (refresh: boolean) => Promise<void>;

  async mounted() {
    await this.fetchStakingDetails(false);
  }
}
</script>

<style scoped lang="scss"></style>
