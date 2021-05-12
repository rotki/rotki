import { Component, Vue } from 'vue-property-decorator';
import { RotkehlchenState } from '@/store/types';
import {
  CRITICAL,
  currentLogLevel,
  DEBUG,
  Level,
  LOG_LEVEL
} from '@/utils/log-level';

const DATA_DIRECTORY = 'rotki_data_directory';

@Component({
  name: 'BackendMixin'
})
export default class BackendMixin extends Vue {
  loglevel: Level = process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL;

  async startBackendWithLogLevel(level: Level) {
    localStorage.setItem(LOG_LEVEL, level);
    await this.$store.commit('setConnected', false);
    await this.$interop.restartBackend(level);
    await this.$store.dispatch('connect');
  }

  setLogLevel(level: Level) {
    localStorage.setItem(LOG_LEVEL, level);
  }

  setDataDirectory(dataDirectory: string) {
    localStorage.setItem(DATA_DIRECTORY, dataDirectory);
  }

  getDataDirectory(): string {
    const persisted = localStorage.getItem(DATA_DIRECTORY);
    if (!persisted) {
      return (this.$store.state as RotkehlchenState).dataDirectory;
    }
    return persisted;
  }

  mounted() {
    this.loglevel = currentLogLevel();
  }

  async restartBackend() {
    await this.startBackendWithLogLevel(this.loglevel);
  }
}
