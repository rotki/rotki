import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import BackendMixin from '@/mixins/backend-mixin';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';

@Component({
  components: {
    ConfirmDialog
  },
  methods: {
    ...mapActions('session', ['logout'])
  }
})
export default class RestoreAssetsDatabase extends Mixins(BackendMixin) {
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
      notify(message, title, Severity.ERROR, true);
    }
  }

  async updateComplete() {
    await this.logout();
    this.$store.commit('setConnected', false);
    if (this.$interop.isPackaged) {
      await this.restartBackend();
    }
    await this.$store.dispatch('connect');
  }

  async confirmHardReset() {
    this.restoreHard = true;
    this.restoreAssets();
  }
}
