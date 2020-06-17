<template>
  <div>
    <v-menu
      id="user-dropdown"
      transition="slide-y-transition"
      max-width="250px"
      offset-y
    >
      <template #activator="{ on }">
        <v-btn
          class="user-dropdown secondary--text text--lighten-2"
          icon
          v-on="on"
        >
          <v-icon>fa fa-user-circle</v-icon>
        </v-btn>
      </template>
      <v-list>
        <v-list-item key="username" class="user-username">
          <v-list-item-title class="font-weight-bold text-center">
            {{ username }}
          </v-list-item-title>
        </v-list-item>
        <v-divider class="mx-4"></v-divider>
        <v-list-item
          key="settings"
          class="user-dropdown__settings"
          to="/settings/general"
        >
          <v-list-item-avatar>
            <v-icon color="primary">fa fa-gear</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>Settings</v-list-item-title>
        </v-list-item>
        <v-list-item
          key="privacy-mode"
          class="user-dropdown__privacy-mode"
          @click="togglePrivacyMode()"
        >
          <v-list-item-avatar>
            <v-icon v-if="privacyMode" color="primary">fa-eye-slash</v-icon>
            <v-icon v-else color="primary">fa-eye</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>Toggle Privacy Mode</v-list-item-title>
        </v-list-item>
        <v-divider class="mx-4"></v-divider>
        <v-list-item
          key="logout"
          class="user-dropdown__logout"
          @click="confirmLogout = true"
        >
          <v-list-item-avatar>
            <v-icon color="primary">fa fa-sign-out</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <confirm-dialog
      :display="confirmLogout"
      title="Confirmation Required"
      message="Are you sure you want to log out of your current rotki session?"
      @confirm="logout()"
      @cancel="confirmLogout = false"
    ></confirm-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';

const { mapState } = createNamespacedHelpers('session');
const { mapState: mapSessionState } = createNamespacedHelpers('session');

@Component({
  components: {
    ConfirmDialog
  },
  computed: {
    ...mapState(['privacyMode']),
    ...mapSessionState(['username'])
  }
})
export default class UserDropdown extends Vue {
  privacyMode!: boolean;
  confirmLogout: boolean = false;

  togglePrivacyMode() {
    this.$store.commit('session/privacyMode', !this.privacyMode);
  }

  async logout() {
    this.confirmLogout = false;
    const { dispatch } = this.$store;

    await dispatch('session/logout');
    if (this.$route.path !== '/') {
      await this.$router.replace('/');
    }
  }
}
</script>

<style scoped></style>
