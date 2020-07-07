<template>
  <div v-if="displayed" class="create-account">
    <v-card-title>Create New Account</v-card-title>
    <v-card-text>
      <v-form ref="form" v-model="valid">
        <v-text-field
          v-model="username"
          autofocus
          class="create-account__fields__username"
          label="Username"
          prepend-icon="fa-user"
          :rules="usernameRules"
          :disabled="loading"
          required
        ></v-text-field>
        <v-text-field
          v-model="password"
          class="create-account__fields__password"
          label="Password"
          prepend-icon="fa-lock"
          :rules="passwordRules"
          :disabled="loading"
          type="password"
          required
        ></v-text-field>
        <v-text-field
          v-model="passwordConfirm"
          class="create-account__fields__password-repeat"
          prepend-icon="fa-repeat"
          :error-messages="errorMessages"
          :rules="passwordConfirmRules"
          :disabled="loading"
          label="Repeat Password"
          type="password"
          required
        >
        </v-text-field>
        <v-checkbox
          v-model="submitUsageAnalytics"
          label="Submit anonymous usage analytics"
          @change="submitUsageanalyticsChanged"
        ></v-checkbox>
        <premium-credentials
          :enabled="premiumEnabled"
          :api-secret="apiSecret"
          :api-key="apiKey"
          :loading="loading"
          @api-key-changed="apiKey = $event"
          @api-secret-changed="apiSecret = $event"
          @enabled-changed="premiumEnabled = $event"
        ></premium-credentials>
      </v-form>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        class="create-account__buttons__cancel"
        depressed
        outlined
        color="primary"
        :disabled="loading"
        @click="cancel()"
      >
        Cancel
      </v-btn>
      <v-btn
        class="create-account__buttons__confirm"
        depressed
        color="primary"
        :disabled="!valid || loading"
        :loading="loading"
        @click="confirm()"
      >
        Create
      </v-btn>
    </v-card-actions>
    <v-dialog persistent max-width="450">
      <v-card
        light
        max-width="500"
        class="mx-auto account-management__premium-dialog"
      >
        <v-card-title class="account-management__premium-dialog__title">
          Anonymous usage analytics
        </v-card-title>
        <v-card-text>
          <v-row class="mx-auto text-justify">
            <v-col cols="2" align-self="center">
              <v-icon color="success" size="48">
                fa fa-info-circle
              </v-icon>
            </v-col>
            <v-col cols="10">
              rotki is a local application and anonymous usage analytics is the
              only way for us to have an idea of how many people use our
              software, where they are from etc. These data are really important
              to us, are completely anonymous and help us create a better
              product for you. Are you sure you want to disable submitting usage
              analytics?
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            class="account-management__premium-dialog__buttons__cancel"
            depressed
            outlined
            @click="acceptAnalytics()"
          >
            Keep usage analytics
          </v-btn>
          <v-btn
            color="primary"
            depressed
            class="account-management__premium-dialog__buttons__confirm"
            @click="rejectAnalytics()"
          >
            Disable usage analytics
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import PremiumCredentials from '@/components/account-management/PremiumCredentials.vue';
import { Credentials } from '@/typing/types';

@Component({
  components: { PremiumCredentials }
})
export default class CreateAccount extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Prop({ required: true, type: Boolean, default: false })
  loading!: boolean;

  username: string = '';
  password: string = '';
  passwordConfirm: string = '';

  premiumEnabled: boolean = false;

  submitUsageAnalytics: boolean = true;
  apiKey: string = '';
  apiSecret: string = '';

  valid: boolean = false;
  errorMessages: string[] = [];

  readonly usernameRules = [
    (v: string) => !!v || 'Please provide a user name',
    (v: string) =>
      (v && /^[0-9a-zA-Z_.-]+$/.test(v)) ||
      'A username must contain only alphanumeric characters and have no spaces'
  ];

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

  @Watch('password')
  onPasswordChange() {
    if (this.password && this.password !== this.passwordConfirm) {
      this.updateConfirmationError();
    } else {
      this.errorMessages.pop();
    }
  }

  @Watch('passwordConfirm')
  onPasswordConfirmationChange() {
    if (this.passwordConfirm && this.passwordConfirm !== this.password) {
      this.updateConfirmationError();
    } else {
      this.errorMessages.pop();
    }
  }

  @Watch('displayed')
  onDisplayChange() {
    this.username = '';
    this.password = '';
    this.passwordConfirm = '';

    const form = this.$refs.form as any;
    if (form) {
      form.reset();
    }
  }

  @Emit()
  submitUsageanalyticsChanged(_enabled: boolean) {
    this.submitUsageAnalytics = _enabled;
    if (!_enabled) {
      // here show the popup
    }
  }

  acceptAnalytics() {
    this.submitUsageAnalytics = true;
  }

  rejectAnalytics() {
    this.submitUsageAnalytics = false;
  }

  confirm() {
    const premiumKeys = {
      apiKey: this.apiKey,
      apiSecret: this.apiSecret
    };

    const accountCredentials: Credentials = {
      username: this.username,
      password: this.password,
      submitUsageAnalytics: this.submitUsageAnalytics
    };

    const credentials: Credentials = {
      ...accountCredentials,
      ...(this.premiumEnabled ? premiumKeys : {})
    };
    this.$emit('confirm', credentials);
  }

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
