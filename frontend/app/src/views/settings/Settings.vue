<template>
  <v-container class="settings">
    <v-row>
      <v-col>
        <h1>Settings</h1>
        <tab-navigation :tab-contents="settingsTabs"></tab-navigation>
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
      name: 'User & Security',
      routeTo: '/settings/user-security'
    }
  ];

  settingsMessages: SettingsMessages = {};

  validateSettingChange(
    targetSetting: string,
    targetState: string,
    message: string = '',
    timeOut: number = 5500
  ) {
    if (targetState === 'success' || targetState === 'error') {
      setTimeout(() => {
        let validationMessage = '';
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
