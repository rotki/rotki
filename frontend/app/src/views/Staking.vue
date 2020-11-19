<template>
  <v-container class="staking">
    <base-page-header :text="$t('staking.title')" />
    <v-container class="staking__content">
      <no-premium-placeholder v-if="!premium" :text="$t('staking.title')" />
      <div v-else>
        <progress-screen v-if="loading">
          <template #message>
            {{ $t('staking.loading') }}
          </template>
        </progress-screen>
        <eth2-staking v-else :refreshing="refreshing" />
      </div>
    </v-container>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { Eth2Staking } from '@/utils/premium';

@Component({
  components: {
    NoPremiumPlaceholder,
    ProgressScreen,
    BasePageHeader,
    Eth2Staking
  },
  methods: {
    ...mapActions('staking', ['fetchStakingDetails'])
  }
})
export default class Staking extends Mixins(PremiumMixin, StatusMixin) {
  readonly section = Section.STAKING_ETH2;
  fetchStakingDetails!: (refresh: boolean) => Promise<void>;

  async mounted() {
    await this.fetchStakingDetails(false);
  }
}
</script>

<style scoped lang="scss">
.staking {
  height: 100%;

  &__content {
    height: calc(100% - 120px);
  }
}
</style>
