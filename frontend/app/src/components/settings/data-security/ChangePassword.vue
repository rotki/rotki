<template>
  <card>
    <template #title>{{ $t('change_password.title') }}</template>

    <v-form ref="form">
      <v-alert
        v-if="premiumSync"
        type="warning"
        prominent
        outlined
        v-text="$t('change_password.sync_warning')"
      />
      <revealable-input
        v-model="currentPassword"
        class="user-security-settings__fields__current-password"
        :label="$t('change_password.labels.password')"
        :rules="passwordRules"
        outlined
      />
      <revealable-input
        v-model="newPassword"
        class="user-security-settings__fields__new-password"
        :label="$t('change_password.labels.new_password')"
        :rules="passwordRules"
        outlined
      />
      <revealable-input
        v-model="newPasswordConfirm"
        class="user-security-settings__fields__new-password-confirm"
        :label="$t('change_password.labels.confirm_password')"
        prepend-icon="mdi-repeat"
        :rules="passwordConfirmRules"
        :error-messages="errorMessages"
        outlined
      />
    </v-form>

    <template #buttons>
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
        v-text="$t('change_password.button')"
      />
    </template>
  </card>
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

  readonly passwordRules = [
    (v: string) =>
      !!v || this.$t('change_password.validation.empty_password').toString()
  ];
  readonly passwordConfirmRules = [
    (v: string) =>
      !!v || this.$t('change_password.validation.empty_confirmation').toString()
  ];

  private updateConfirmationError() {
    if (this.errorMessages.length > 0) {
      return;
    }
    this.errorMessages.push(
      this.$t('change_password.validation.password_missmatch').toString()
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
