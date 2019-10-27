<template>
  <v-menu id="user-dropdown" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text class="user-dropdown" v-on="on">
        <v-icon>fa fa-user</v-icon>
      </v-btn>
    </template>

    <v-list>
      <v-list-item
        key="user-settings"
        class="user-dropdown__user-settings"
        to="/settings/user"
      >
        <v-list-item-avatar>
          <v-icon color="primary">fa fa-user</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>User Settings</v-list-item-title>
      </v-list-item>

      <v-list-item
        key="accounting-settings"
        class="user-dropdown__accounting-settings"
        to="/settings/accounting"
      >
        <v-list-item-avatar>
          <v-icon color="primary">fa fa-book</v-icon>
        </v-list-item-avatar>
        <v-list-item-title>Accounting Settings</v-list-item-title>
      </v-list-item>

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

      <v-divider></v-divider>

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
    <confirm-dialog
      :display="confirmLogout"
      title="Confirmation Required"
      message="Are you sure you want to log out of your current rotkehlchen session?"
      @confirm="logout()"
      @cancel="confirmLogout = false"
    ></confirm-dialog>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';

@Component({
  components: {
    ConfirmDialog
  }
})
export default class UserDropdown extends Vue {
  confirmLogout: boolean = false;

  async logout() {
    this.confirmLogout = false;
    const { dispatch } = this.$store;

    await dispatch('session/logout');
    this.$router.push({ name: 'dashboard' });
  }
}
</script>

<style scoped></style>
