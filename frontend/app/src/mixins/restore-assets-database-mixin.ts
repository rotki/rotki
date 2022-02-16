import { Severity } from '@rotki/common/lib/messages';
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import BackendMixin from '@/mixins/backend-mixin';
import { useNotifications } from '@/store/notifications';
import { useMainStore } from '@/store/store';

@Component({
  methods: {
    ...mapActions('session', ['logout'])
  }
})
export default class RestoreAssetsDatabaseMixin extends Mixins(BackendMixin) {
  confirmRestore: boolean = false;
  done: boolean = false;
  restoreMode: string = 'hard';
  restoreHard: boolean = false;
  doubleConfirmation: boolean = false;
  logout!: () => Promise<void>;

  activateRestoreAssets() {
    this.confirmRestore = true;
  }

  async restoreAssets() {
    try {
      this.confirmRestore = false;
      const updated = await this.$api.assets.restoreAssetsDatabase(
        this.restoreMode,
        this.restoreHard
      );
      if (updated) {
        this.done = true;
        this.restoreHard = false;
      }
    } catch (e: any) {
      const title = this.$t('asset_update.restore.title').toString();
      const message = e.toString();
      if (message.includes('There are assets that can not')) {
        this.doubleConfirmation = true;
        this.confirmRestore = false;
      }
      const { notify } = useNotifications();
      notify({
        title,
        message,
        severity: Severity.ERROR,
        display: true
      });
    }
  }

  async updateComplete() {
    const { connect, setConnected } = useMainStore();
    await this.logout();
    setConnected(false);
    if (this.$interop.isPackaged) {
      await this.restartBackend();
    }
    await connect();
  }

  async confirmHardReset() {
    this.restoreHard = true;
    this.restoreAssets();
  }
}
