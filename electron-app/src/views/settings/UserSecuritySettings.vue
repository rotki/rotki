<template>
  <v-container id="settings-user-security">
    <v-row no-gutters>
      <v-col>
        <v-card>
          <v-card-title>User Account & Security</v-card-title>
          <v-form ref="form">
            <v-card-text>
              <revealable-input
                v-model="currentPassword"
                class="settings-general__account-and-security__fields__current-password"
                label="Current Password"
                :rules="passwordRules"
              ></revealable-input>
              <revealable-input
                v-model="newPassword"
                class="settings-general__account-and-security__fields__new-password"
                label="New Password"
                :rules="passwordRules"
              ></revealable-input>
              <revealable-input
                v-model="newPasswordConfirm"
                class="settings-general__account-and-security__fields__new-password-confirm"
                label="Confirm New Password"
                icon="fa-repeat"
                :rules="passwordConfirmRules"
                :error-messages="errorMessages"
              ></revealable-input>
            </v-card-text>
            <v-card-actions>
              <v-btn
                depressed
                class="settings-general__account-and-security__buttons__change-password"
                color="primary"
                :disabled="
                  !(
                    currentPassword &&
                    newPassword &&
                    newPassword === newPasswordConfirm
                  )
                "
                @click="changePassword()"
              >
                Change Password
              </v-btn>
            </v-card-actions>
          </v-form>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { Message } from '@/store/store';

const { mapState } = createNamespacedHelpers('session');

@Component({
  components: { RevealableInput },
  computed: {
    ...mapState(['username'])
  }
})
export default class UserSecuritySettings extends Vue {
  currentPassword: string = '';
  newPassword: string = '';
  newPasswordConfirm: string = '';
  errorMessages: string[] = [];
  username!: string;

  readonly passwordRules = [(v: string) => !!v || 'Please provide a password'];
  readonly passwordConfirmRules = [
    (v: string) => !!v || 'Please provide a password confirmation'
  ];

  private updateConfirmationError() {
    if (this.errorMessages.length > 0) {
      return;
    }
    this.errorMessages.push(
      'The password confirmation does not match the provided password'
    );
  }

  @Watch('newPassword')
  onNewPasswordChange() {
    if (this.newPassword && this.newPassword !== this.newPasswordConfirm) {
      this.updateConfirmationError();
    } else {
      this.errorMessages.pop();
    }
  }

  @Watch('newPasswordConfirm')
  onNewPasswordConfirmationChange() {
    if (
      this.newPasswordConfirm &&
      this.newPasswordConfirm !== this.newPassword
    ) {
      this.updateConfirmationError();
    } else {
      this.errorMessages.pop();
    }
  }

  changePassword() {
    const currentPassword = this.currentPassword;
    const newPassword = this.newPassword;
    const newPasswordConfirm = this.newPasswordConfirm;

    if (currentPassword && newPassword === newPasswordConfirm) {
      const { commit } = this.$store;

      this.$api
        .changeUserPassword(this.username, currentPassword, newPassword)
        .then(() => {
          commit('setMessage', {
            title: 'Success',
            description: 'Successfully changed user password',
            success: true
          } as Message);
          (this.$refs.form as Vue & { reset: () => boolean }).reset();
          (this.$refs.form as Vue & {
            resetValidation: () => boolean;
          }).resetValidation();
        })
        .catch((reason: Error) => {
          commit('setMessage', {
            title: 'Error',
            description: reason.message || 'Error while changing user password',
            success: false
          } as Message);
        });
    }
  }
}
</script>

<style scoped></style>
