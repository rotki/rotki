import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { MODULE_BALANCER, MODULE_UNISWAP } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';

@Component({
  computed: {
    ...mapGetters('session', ['activeModules'])
  }
})
export default class DefiModuleMixin extends Vue {
  activeModules!: SupportedModules[];

  get MODULE_UNISWAP(): string {
    return MODULE_UNISWAP;
  }

  get balancerModule(): typeof MODULE_BALANCER {
    return MODULE_BALANCER;
  }

  get isUniswapEnabled(): boolean {
    return this.isModuleEnabled(MODULE_UNISWAP);
  }

  get isBalancerEnabled(): boolean {
    return this.isModuleEnabled(MODULE_BALANCER);
  }

  isModuleEnabled(module: SupportedModules): boolean {
    return this.activeModules.includes(module);
  }

  isAnyModuleEnabled(modules: SupportedModules[]): boolean {
    return (
      this.activeModules.filter(module => modules.includes(module)).length > 0
    );
  }
}
