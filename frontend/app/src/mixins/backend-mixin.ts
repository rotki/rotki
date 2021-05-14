import { Component, Vue } from 'vue-property-decorator';
import { BackendOptions } from '@/electron-main/ipc';
import { Writeable } from '@/types';
import { CRITICAL, DEBUG, Level, LOG_LEVEL } from '@/utils/log-level';

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

const loadUserConfig: () => Partial<BackendOptions> = () => {
  const defaultConfig: Partial<BackendOptions> = {
    loglevel: process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL
  };
  try {
    const opts = localStorage.getItem(BACKEND_OPTIONS);
    const options: Writeable<Partial<BackendOptions>> = opts
      ? JSON.parse(opts)
      : defaultConfig;
    const loglevel = localStorage.getItem(LOG_LEVEL);
    if (loglevel) {
      options.loglevel = loglevel as Level;
      saveUserConfig(options);
      localStorage.removeItem(LOG_LEVEL);
    }
    return options;
  } catch (e) {
    return defaultConfig;
  }
};

const saveUserConfig = (config: Partial<BackendOptions>) => {
  const options = JSON.stringify(config);
  localStorage.setItem(BACKEND_OPTIONS, options);
};

@Component({
  name: 'BackendMixin'
})
export default class BackendMixin extends Vue {
  loglevel: Level = process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL;
  fileConfig: Partial<BackendOptions> = {};
  userConfig: Partial<BackendOptions> = {};

  get config(): Partial<BackendOptions> {
    return { ...this.userConfig, ...this.fileConfig };
  }

  async restartBackendWithOptions(options: Partial<BackendOptions>) {
    await this.$store.commit('setConnected', false);
    await this.$interop.restartBackend(options);
    await this.$store.dispatch('connect');
  }

  async mounted() {
    this.userConfig = loadUserConfig();
    this.fileConfig = await this.$interop.backendConfig();
  }

  saveOptions() {
    saveUserConfig(this.userConfig);
  }

  async restartBackend() {
    await this.restartBackendWithOptions(this.config);
  }
}
