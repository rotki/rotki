import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { MODULE_UNISWAP } from '@/services/session/consts';
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

  get isUniswapEnabled(): boolean {
    return this.activeModules.includes(MODULE_UNISWAP);
  }
}
