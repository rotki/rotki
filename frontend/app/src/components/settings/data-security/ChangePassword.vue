<template>
  <v-row no-gutters>
    <v-col>
      <v-card>
        <v-card-title>User Account & Security</v-card-title>
        <v-form ref="form">
          <v-card-text>
            <v-alert v-if="premiumSync" type="warning" prominent outlined>
              Changing the password with premium sync enabled will affect other
              synced instances of the application. Upon login with other synced
              instances, you will be asked to overwrite the local DB with the
              synced version on the server. After that, you must log in with the
              newly set password.
            </v-alert>
            <revealable-input
              v-model="currentPassword"
              class="user-security-settings__fields__current-password"
              label="Current Password"
              :rules="passwordRules"
            ></revealable-input>
            <revealable-input
              v-model="newPassword"
              class="user-security-settings__fields__new-password"
              label="New Password"
              :rules="passwordRules"
            ></revealable-input>
            <revealable-input
              v-model="newPasswordConfirm"
              class="user-security-settings__fields__new-password-confirm"
              label="Confirm New Password"
              icon="fa-repeat"
              :rules="passwordConfirmRules"
              :error-messages="errorMessages"
            ></revealable-input>
          </v-card-text>
          <v-card-actions>
            <v-btn
              depressed
              class="user-security-settings__buttons__change-password"
              color="primary"
              :disabled="
                !(
                  currentPassword &&
                  newPassword &&
                  newPassword === newPasswordConfirm
                )
              "
              @click="change()"
            >
              Change Password
            </v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { ChangePasswordPayload } from '@/store/session/types';
import { ActionStatus } from '@/store/types';

type Form = {
  reset: () => boolean;
  resetValidation: () => boolean;
};

@Component({
  components: { RevealableInput },
  computed: {
    ...mapState('session', ['premiumSync'])
  },
  methods: {
    ...mapActions('session', ['changePassword'])
  }
})
export default class ChangePassword extends Vue {
  currentPassword: string = '';
  newPassword: string = '';
  newPasswordConfirm: string = '';
  errorMessages: string[] = [];
  premiumSync!: string;
  changePassword!: (payload: ChangePasswordPayload) => Promise<ActionStatus>;

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

  private reset() {
    const form = this.$refs.form as Vue & Form;
    form.reset();
    form.resetValidation();
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

  async change() {
    const currentPassword = this.currentPassword;
    const newPassword = this.newPassword;
    const newPasswordConfirm = this.newPasswordConfirm;

    if (!(currentPassword && newPassword === newPasswordConfirm)) {
      return;
    }

    const { success } = await this.changePassword({
      currentPassword,
      newPassword
    });

    if (success) {
      this.reset();
    }
  }
}
</script>
