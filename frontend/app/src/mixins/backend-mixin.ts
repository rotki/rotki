import { Component, Vue } from 'vue-property-decorator';
import { loadUserOptions, saveUserOptions } from '@/composables/backend';
import { BackendOptions } from '@/electron-main/ipc';
import { useMainStore } from '@/store/store';
import { LogLevel } from '@/utils/log-level';
import { getDefaultLogLevel, setLevel } from '@/utils/logging';

@Component({
  name: 'BackendMixin'
})
export default class BackendMixin extends Vue {
  loglevel: LogLevel = this.defaultLogLevel;
  fileConfig: Partial<BackendOptions> = {};
  userOptions: Partial<BackendOptions> = {};
  defaultLogDirectory: string = '';

  get defaultLogLevel(): LogLevel {
    return getDefaultLogLevel();
  }

  get options(): Partial<BackendOptions> {
    return { ...this.userOptions, ...this.fileConfig };
  }

  async restartBackendWithOptions(options: Partial<BackendOptions>) {
    const { setConnected, connect } = useMainStore();
    await setConnected(false);
    await this.$interop.restartBackend(options);
    await connect();
  }

  async mounted() {
    await this.load();
    this.loaded();
    setLevel(this.options.loglevel);
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
    const { logDirectory, dataDirectory } = this.userOptions;
    const updatedOptions = {
      logDirectory,
      dataDirectory,
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
