<template>
  <li id="user-dropdown" class="dropdown">
    <a class="dropdown-toggle" data-toggle="dropdown" href="#">
      <i class="fa fa-user fa-fw"></i> <i class="fa fa-caret-down"></i>
    </a>
    <ul class="dropdown-menu dropdown-user">
      <li id="user_settings_button">
        <router-link to="/settings/user">
          <i class="fa fa-user fa-fw"></i> User Settings
        </router-link>
      </li>
      <li id="accounting_settings_button">
        <router-link to="/settings/accounting">
          <i class="fa fa-book fa-fw"></i>Accounting Settings
        </router-link>
      </li>
      <li id="settingsbutton">
        <router-link to="/settings/general">
          <i class="fa fa-gear fa-fw"></i> Settings
        </router-link>
      </li>
      <li class="divider"></li>
      <li id="logout_button">
        <a @click="logoutClicked()">
          <i class="fa fa-sign-out fa-fw"></i> Logout
        </a>
      </li>
    </ul>
  </li>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class Settings extends Vue {
  logoutClicked() {
    this.$store.commit('logout', true);
  }
}
</script>

<style scoped></style>
