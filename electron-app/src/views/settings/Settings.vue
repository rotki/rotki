<template>
  <v-container class="settings">
    <v-row>
      <v-col>
        <h1>Settings</h1>
        <tab-navigation :tab-contents="settingsTabs"></tab-navigation>
      </v-col>
    </v-row>
    <v-slide-x-transition>
      <router-view />
    </v-slide-x-transition>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import TabNavigation from '@/components/helper/TabNavigation.vue';

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
  settingsTabs = [
    {
      name: 'General',
      routerTo: '/settings/general'
    },
    {
      name: 'Accounting',
      routerTo: '/settings/accounting'
    },
    {
      name: 'User & Security',
      routerTo: '/settings/usersecurity'
    }
  ];

  settingsMessages: SettingsMessages = {};

  validateSettingChange(
    targetSetting: string,
    targetState: string,
    message: string = '',
    timeOut: number = 10000
  ) {
    if (targetState === 'success' || targetState === 'error') {
      setTimeout(() => {
        this.settingsMessages[targetSetting][targetState] = `Setting${
          targetState === 'error' ? ' not ' : ' '
        }saved${message !== '' ? ': ' + message : ''}`;
      }, 500);
      setTimeout(() => {
        this.settingsMessages[targetSetting][targetState] = '';
      }, timeOut);
    }
  }
}
</script>

<style scoped lang="scss"></style>
