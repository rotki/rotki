import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import { BaseMessage, SettingsMessages } from '@/components/settings/utils';
import i18n from '@/i18n';
import { ActionStatus } from '@/store/types';
import { FrontendSettingsPayload } from '@/types/frontend-settings';
import {
  AccountingSettings,
  GeneralSettings,
  SettingsUpdate
} from '@/types/user';

type TargetState = keyof BaseMessage;

@Component({
  computed: {
    ...mapState('session', ['generalSettings', 'accountingSettings'])
  },
  methods: {
    ...mapActions('session', ['settingsUpdate']),
    ...mapActions('settings', ['updateSetting'])
  }
})
export default class SettingsMixin<T extends string> extends Vue {
  settingsUpdate!: (update: SettingsUpdate) => Promise<ActionStatus>;
  updateSetting!: (payload: FrontendSettingsPayload) => Promise<ActionStatus>;
  generalSettings!: GeneralSettings;
  accountingSettings!: AccountingSettings;

  settingsMessages: SettingsMessages<T> | null = null;

  validateSettingChange(
    targetSetting: T,
    targetState: TargetState,
    message: string = '',
    timeOut: number = 5500
  ) {
    if (!(targetState === 'success' || targetState === 'error')) {
      return;
    }

    const settingsMessage = this.settingsMessages?.[targetSetting];
    if (!settingsMessage) {
      return;
    }
    setTimeout(() => {
      let validationMessage: string =
        targetState === 'error'
          ? i18n.t('settings.not_saved').toString()
          : i18n.t('settings.saved').toString();
      if (message) {
        validationMessage += `: ${message}`;
      }

      settingsMessage[targetState] = validationMessage;
    }, 200);
    setTimeout(() => {
      settingsMessage[targetState] = '';
    }, timeOut);
  }

  async modifyFrontendSetting(
    payload: FrontendSettingsPayload,
    setting: T,
    messages: BaseMessage
  ): Promise<ActionStatus> {
    const result = await this.updateSetting(payload);
    const { success } = result;

    this.validateSettingChange(
      setting,
      success ? 'success' : 'error',
      success ? messages.success : messages.error
    );
    return result;
  }
}
