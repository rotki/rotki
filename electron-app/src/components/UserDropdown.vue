<template>
  <v-menu id="user-dropdown" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon>fa fa-user</v-icon>
      </v-btn>
    </template>

    <v-list>
      <v-list-item
        id="user_settings_button"
        key="user-settings"
        to="/settings/user"
      >
        <v-list-item-avatar>
          <v-icon color="primary">fa fa-user</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>User Settings</v-list-item-title>
      </v-list-item>

      <v-list-item
        id="accounting_settings_button"
        key="accounting-settings"
        to="/settings/accounting"
      >
        <v-list-item-avatar>
          <v-icon color="primary">fa fa-book</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>Accounting Settings</v-list-item-title>
      </v-list-item>

      <v-list-item id="settings_button" key="settings" to="/settings/general">
        <v-list-item-avatar>
          <v-icon color="primary">fa fa-gear</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>Settings</v-list-item-title>
      </v-list-item>

      <v-divider></v-divider>

      <v-list-item id="logout_button" key="logout" @click="logout">
        <v-list-item-avatar>
          <v-icon color="primary">fa fa-sign-out</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>Logout</v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class UserDropdown extends Vue {
  logout() {
    const { commit } = this.$store;
    commit('session/reset');
    commit('notifications/reset');
    commit('reports/reset');
    commit('balances/reset');
    commit('tasks/reset');
    this.$router.push({ name: 'dashboard' });
  }
}
</script>

<style scoped></style>
