<template>
  <div>
    <v-menu
      id="user-dropdown"
      transition="slide-y-transition"
      max-width="250px"
      offset-y
    >
      <template #activator="{ on }">
        <menu-tooltip-button
          tooltip="Account"
          class-name="user-dropdown secondary--text text--lighten-2"
          :on-menu="on"
        >
          <v-icon>mdi-account-circle</v-icon>
        </menu-tooltip-button>
      </template>
      <v-list data-cy="user-dropdown">
        <v-list-item key="username" class="user-username">
          <v-list-item-title class="font-weight-bold text-center">
            {{ username }}
          </v-list-item-title>
        </v-list-item>
        <v-divider class="mx-4" />
        <v-list-item
          key="settings"
          class="user-dropdown__settings"
          to="/settings/general"
        >
          <v-list-item-avatar>
            <v-icon color="primary">mdi-cog</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ $t('user_dropdown.settings') }}
          </v-list-item-title>
        </v-list-item>
        <v-list-item
          key="privacy-mode"
          class="user-dropdown__privacy-mode"
          @click="togglePrivacyMode()"
        >
          <v-list-item-avatar>
            <v-icon v-if="privacyMode" color="primary">mdi-eye-off</v-icon>
            <v-icon v-else color="primary">mdi-eye</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ $t('user_dropdown.toggle_privacy') }}
          </v-list-item-title>
        </v-list-item>
        <v-divider class="mx-4" />
        <v-list-item
          key="logout"
          class="user-dropdown__logout"
          @click="confirmLogout = true"
        >
          <v-list-item-avatar>
            <v-icon color="primary">mdi-logout-variant</v-icon>
          </v-list-item-avatar>
          <v-list-item-title>
            {{ $t('user_dropdown.logout') }}
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
    <confirm-dialog
      :display="confirmLogout"
      :title="$t('user_dropdown.confirmation.title')"
      :message="$t('user_dropdown.confirmation.message')"
      @confirm="logout()"
      @cancel="confirmLogout = false"
    />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

@Component({
  components: {
    ConfirmDialog,
    MenuTooltipButton
  },
  computed: {
    ...mapState('session', ['privacyMode', 'username'])
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
