<template>
  <module-not-active v-if="!moduleEnabled" :modules="module" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ $t('adex_page.loading') }}
    </template>
  </progress-screen>
  <adex-staking
    v-else
    :history-refreshing="secondaryLoading || secondaryRefreshing"
    :refreshing="refreshing"
  />
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import DefiModuleMixin from '@/mixins/defi-module-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { AdexStaking } from '@/premium/premium';
import { MODULE_ADEX } from '@/services/session/consts';
import { Section } from '@/store/const';

@Component({
  components: { ModuleNotActive, AdexStaking, ProgressScreen },
  methods: {
    ...mapActions('staking', ['fetchAdex'])
  }
})
export default class AdexPage extends Mixins(StatusMixin, DefiModuleMixin) {
  readonly module = [MODULE_ADEX];
  section = Section.STAKING_ADEX;
  secondSection = Section.STAKING_ADEX_HISTORY;

  fetchAdex!: (refresh: boolean) => Promise<void>;

  get moduleEnabled(): boolean {
    return this.isModuleEnabled(MODULE_ADEX);
  }

  async mounted() {
    await this.fetchAdex(false);
  }
}
</script>

<style scoped lang="scss"></style>
