import { Component, Vue } from 'vue-property-decorator';
import { BackendOptions } from '@/electron-main/ipc';
import { Writeable } from '@/types';
import { CRITICAL, DEBUG, Level, LOG_LEVEL } from '@/utils/log-level';

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

const loadUserOptions: () => Partial<BackendOptions> = () => {
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
      saveUserOptions(options);
      localStorage.removeItem(LOG_LEVEL);
    }
    return options;
  } catch (e) {
    return defaultConfig;
  }
};

const saveUserOptions = (config: Partial<BackendOptions>) => {
  const options = JSON.stringify(config);
  localStorage.setItem(BACKEND_OPTIONS, options);
};

@Component({
  name: 'BackendMixin'
})
export default class BackendMixin extends Vue {
  loglevel: Level = this.defaultLogLevel;
  fileConfig: Partial<BackendOptions> = {};
  userOptions: Partial<BackendOptions> = {};
  defaultLogDirectory: string = '';

  get defaultLogLevel(): Level {
    return process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL;
  }

  get options(): Partial<BackendOptions> {
    return { ...this.userOptions, ...this.fileConfig };
  }

  async restartBackendWithOptions(options: Partial<BackendOptions>) {
    await this.$store.commit('setConnected', false);
    await this.$interop.restartBackend(options);
    await this.$store.dispatch('connect');
  }

  async mounted() {
    await this.load();
    this.loaded();
  }

  private async load() {
    if (!this.$interop.isPackaged) {
      return;
    }
    this.userOptions = loadUserOptions();
    this.fileConfig = await this.$interop.config(false);
    const { logDirectory } = await this.$interop.config(true);
    if (logDirectory) {
      this.defaultLogDirectory = logDirectory;
    }
  }

  loaded() {}

  async saveOptions(options: Partial<BackendOptions>) {
    const { logDirectory, dataDirectory, loglevel } = this.userOptions;
    const updatedOptions = {
      logDirectory,
      dataDirectory,
      loglevel,
      ...options
    };
    saveUserOptions(updatedOptions);
    this.userOptions = updatedOptions;
    await this.restartBackendWithOptions(this.options);
  }

  async resetOptions() {
    saveUserOptions({});
    this.userOptions = {};
    await this.restartBackendWithOptions(this.options);
  }

  async restartBackend() {
    if (!this.$interop.isPackaged) {
      return;
    }
    await this.load();
    await this.restartBackendWithOptions(this.options);
  }
}
