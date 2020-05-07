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
      name: 'User Security',
      routerTo: '/settings/user'
    }
  ];
}
</script>

<style scoped lang="scss"></style>
