<template>
  <module-not-active v-if="!moduleEnabled" :modules="module" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ $t('adex_page.loading') }}
    </template>
  </progress-screen>
  <div v-else>
    <active-modules :modules="module" class="adex__modules" />
    <adex-staking
      :history-refreshing="secondaryLoading || secondaryRefreshing"
      :refreshing="refreshing"
    />
  </div>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import ModuleMixin from '@/mixins/module-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { AdexStaking } from '@/premium/premium';
import { MODULE_ADEX } from '@/services/session/consts';
import { Section } from '@/store/const';

@Component({
  components: { ActiveModules, ModuleNotActive, AdexStaking, ProgressScreen },
  methods: {
    ...mapActions('staking', ['fetchAdex'])
  }
})
export default class AdexPage extends Mixins(StatusMixin, ModuleMixin) {
  readonly module = [MODULE_ADEX];
  section = Section.STAKING_ADEX;
  secondSection = Section.STAKING_ADEX_HISTORY;

  fetchAdex!: (refresh: boolean) => Promise<void>;

  get moduleEnabled(): boolean {
    return this.isModuleEnabled(MODULE_ADEX);
  }

  async mounted() {
    if (!this.moduleEnabled) {
      return;
    }
    await this.fetchAdex(false);
  }
}
</script>

<style scoped lang="scss">
.adex {
  &__modules {
    display: inline-flex;
    position: absolute;
    right: 65px;
    top: 48px;
  }
}
</style>
