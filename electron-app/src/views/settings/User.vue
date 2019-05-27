<template>
  <v-container>
    <v-layout>
      <v-flex>
        <h1 class="page-header">User Settings</h1>
      </v-flex>
    </v-layout>
    <premium-settings></premium-settings>
    <div id="settings-user"></div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { create_or_reload_usersettings } from '@/legacy/user_settings';
import PremiumSettings from '@/components/settings/PremiumSettings.vue';

@Component({
  components: { PremiumSettings }
})
export default class User extends Vue {
  mounted() {
    create_or_reload_usersettings();
  }
}
</script>

<style scoped></style>
