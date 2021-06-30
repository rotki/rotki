<template>
  <v-container>
    <module-not-active v-if="!moduleEnabled" :modules="module" />
    <progress-screen v-else-if="loading">
      <template #message>
        {{ $t('eth2page.loading') }}
      </template>
    </progress-screen>
    <div v-else>
      <active-modules :modules="module" class="eth2-page__modules" />
      <eth2-staking
        :refreshing="refreshing"
        :secondary-refreshing="secondaryRefreshing"
      />
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';

import { mapActions } from 'vuex';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ModuleMixin from '@/mixins/module-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Eth2Staking } from '@/premium/premium';
import { MODULE_ETH2 } from '@/services/session/consts';
import { Section } from '@/store/const';

@Component({
  components: { ActiveModules, ModuleNotActive, ProgressScreen, Eth2Staking },
  methods: {
    ...mapActions('staking', ['fetchStakingDetails'])
  }
})
export default class Eth2Page extends Mixins(StatusMixin, ModuleMixin) {
  readonly module = [MODULE_ETH2];
  readonly section = Section.STAKING_ETH2;
  readonly secondSection = Section.STAKING_ETH2_DEPOSITS;
  fetchStakingDetails!: (refresh: boolean) => Promise<void>;

  get moduleEnabled(): boolean {
    return this.isModuleEnabled(MODULE_ETH2);
  }

  async mounted() {
    if (!this.moduleEnabled) {
      return;
    }
    await this.fetchStakingDetails(false);
  }
}
</script>

<style scoped lang="scss">
.eth2-page {
  &__modules {
    display: inline-flex;
    position: absolute;
    right: 65px;
    top: 35px;
  }
}
</style>
