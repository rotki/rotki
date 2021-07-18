import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import {
  QueriedAddresses,
  QueriedAddressPayload,
  SupportedModules
} from '@/services/session/types';
import { SettingsUpdate } from '@/typing/types';

@Component({
  computed: {
    ...mapGetters('session', ['activeModules']),
    ...mapState('session', ['queriedAddresses'])
  },
  methods: {
    ...mapActions('session', [
      'fetchQueriedAddresses',
      'addQueriedAddress',
      'updateSettings'
    ])
  }
})
export default class ModuleMixin extends Vue {
  activeModules!: SupportedModules[];
  queriedAddresses!: QueriedAddresses;
  fetchQueriedAddresses!: () => Promise<void>;
  addQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  updateSettings!: (update: SettingsUpdate) => Promise<void>;

  isModuleEnabled(module: SupportedModules): boolean {
    return this.activeModules.includes(module);
  }

  isAnyModuleEnabled(modules: SupportedModules[]): boolean {
    return (
      this.activeModules.filter(module => modules.includes(module)).length > 0
    );
  }

  async activateModules(modules: SupportedModules[]) {
    await this.updateSettings({ active_modules: modules });
  }
}
