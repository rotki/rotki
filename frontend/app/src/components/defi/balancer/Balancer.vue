<template>
  <no-premium-placeholder v-if="!premium" :text="$t('balancer.premium')" />
  <module-not-active v-else-if="!isBalancerEnabled" :module="balancerModule" />
  <progress-screen v-else-if="loading">
    <template #message>
      {{ $t('balancer.loading') }}
    </template>
  </progress-screen>
  <v-container v-else>
    <balancer-balances class="mt-4" />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import DefiModuleMixin from '@/mixins/defi-module-mixin';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { BalancerBalances } from '@/utils/premium';

@Component({
  components: {
    BalancerBalances,
    NoPremiumPlaceholder,
    BaseExternalLink,
    ProgressScreen,
    ModuleNotActive
  },
  computed: {},
  methods: {
    ...mapActions('defi', ['fetchBalancerBalances'])
  }
})
export default class Balancer extends Mixins(
  StatusMixin,
  DefiModuleMixin,
  PremiumMixin
) {
  readonly section = Section.DEFI_BALANCER_BALANCES;
  fetchBalancerBalances!: (refresh: boolean) => Promise<void>;

  mounted() {
    this.fetchBalancerBalances(false);
  }
}
</script>

<style scoped lang="scss"></style>
