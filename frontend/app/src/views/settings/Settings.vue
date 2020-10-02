<template>
  <v-container class="settings">
    <v-row>
      <v-col>
        <h1>{{ $t('settings.title') }}</h1>
        <tab-navigation :tab-contents="settingsTabs" />
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import TabNavigation, {
  TabContent
} from '@/components/helper/TabNavigation.vue';

export interface SettingsMessages {
  [index: string]: {
    success: string;
    error: string;
  };
}

@Component({
  components: { TabNavigation }
})
export default class Settings extends Vue {
  readonly settingsTabs: TabContent[] = [
    {
      name: 'General',
      routeTo: '/settings/general'
    },
    {
      name: 'Accounting',
      routeTo: '/settings/accounting'
    },
    {
      name: 'Data & Security',
      routeTo: '/settings/data-security'
    },
    {
      name: 'Defi',
      routeTo: '/settings/defi'
    }
  ];

  settingsMessages: SettingsMessages = {};

  validateSettingChange(
    targetSetting: string,
    targetState: 'success' | 'error',
    message: string = '',
    timeOut: number = 5500
  ) {
    if (targetState === 'success' || targetState === 'error') {
      setTimeout(() => {
        let validationMessage: string;
        if (targetState === 'error') {
          validationMessage = 'Setting not saved';
        } else {
          validationMessage = 'Setting saved';
        }

        if (message) {
          validationMessage += `: ${message}`;
        }

        this.settingsMessages[targetSetting][targetState] = validationMessage;
      }, 200);
      setTimeout(() => {
        this.settingsMessages[targetSetting][targetState] = '';
      }, timeOut);
    }
  }
}
</script>

<style scoped lang="scss"></style>
