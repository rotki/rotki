<template>
  <div v-if="displayed" class="create-account">
    <div class="text-h6 text--primary create-account__header">
      {{ $t('create_account.title') }}
    </div>
    <v-stepper v-model="step">
      <v-stepper-header>
        <v-stepper-step step="1" :complete="step > 1">
          {{ $t('create_account.select_credentials.title') }}
        </v-stepper-step>
        <v-divider />
        <v-stepper-step step="2">
          {{ $t('create_account.usage_analytics.title') }}
        </v-stepper-step>
      </v-stepper-header>
      <v-stepper-items>
        <v-stepper-content step="1">
          <v-card-text>
            <v-form ref="form" v-model="valid">
              <v-text-field
                v-model="username"
                autofocus
                class="create-account__fields__username"
                :label="$t('create_account.select_credentials.label_username')"
                prepend-icon="mdi-account"
                :rules="usernameRules"
                :disabled="loading"
                required
              />
              <revealable-input
                v-model="password"
                class="create-account__fields__password"
                :label="$t('create_account.select_credentials.label_password')"
                prepend-icon="mdi-lock"
                :rules="passwordRules"
                :disabled="loading"
                required
              />
              <revealable-input
                v-model="passwordConfirm"
                class="create-account__fields__password-repeat"
                prepend-icon="mdi-repeat"
                :error-messages="errorMessages"
                :rules="passwordConfirmRules"
                :disabled="loading"
                :label="
                  $t('create_account.select_credentials.label_password_repeat')
                "
                required
              />
              <v-checkbox
                v-model="userPrompted"
                class="create-account__boxes__user-prompted"
                :label="
                  $t(
                    'create_account.select_credentials.label_password_backup_reminder'
                  )
                "
              />
              <premium-credentials
                :enabled="premiumEnabled"
                :api-secret="apiSecret"
                :api-key="apiKey"
                :loading="loading"
                @api-key-changed="apiKey = $event"
                @api-secret-changed="apiSecret = $event"
                @enabled-changed="premiumEnabled = $event"
              />
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              class="create-account__buttons__cancel"
              depressed
              outlined
              color="primary"
              :disabled="loading"
              @click="cancel()"
            >
              {{ $t('create_account.select_credentials.button_cancel') }}
            </v-btn>
            <v-btn
              class="create-account__buttons__continue"
              depressed
              color="primary"
              :disabled="!valid || loading || !userPrompted"
              :loading="loading"
              @click="step = 2"
            >
              {{ $t('create_account.select_credentials.button_continue') }}
            </v-btn>
          </v-card-actions>
        </v-stepper-content>
        <v-stepper-content step="2">
          <v-card
            light
            max-width="500"
            class="mx-auto create-account__analytics"
          >
            <v-card-text>
              <v-alert
                outlined
                prominent
                color="primary"
                class="mx-auto text-justify text-body-2 create-account__analytics__content"
              >
                {{ $t('create_account.usage_analytics.description') }}
              </v-alert>
              <v-alert v-if="error" type="error" outlined>
                {{ error }}
              </v-alert>
              <v-row no-gutters>
                <v-col>
                  <v-checkbox
                    v-model="submitUsageAnalytics"
                    :disabled="loading"
                    :label="$t('create_account.usage_analytics.label_confirm')"
                  />
                </v-col>
              </v-row>
            </v-card-text>
            <v-card-actions>
              <v-spacer />
              <v-btn
                color="primary"
                class="create-account__analytics__buttons__back"
                depressed
                :disabled="loading"
                outlined
                @click="back"
              >
                {{ $t('create_account.usage_analytics.button_back') }}
              </v-btn>
              <v-btn
                color="primary"
                depressed
                :disabled="loading"
                :loading="loading"
                class="create-account__analytics__buttons__confirm"
                @click="confirm()"
              >
                {{ $t('create_account.usage_analytics.button_create') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-stepper-content>
      </v-stepper-items>
    </v-stepper>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import PremiumCredentials from '@/components/account-management/PremiumCredentials.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { Credentials } from '@/typing/types';

@Component({
  components: { RevealableInput, PremiumCredentials }
})
export default class CreateAccount extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Prop({ required: true, type: Boolean, default: false })
  loading!: boolean;

  @Prop({ required: false, type: String, default: '' })
  error!: string;

  username: string = '';
  password: string = '';
  passwordConfirm: string = '';

  premiumEnabled: boolean = false;
  userPrompted: boolean = false;

  submitUsageAnalytics: boolean = true;
  apiKey: string = '';
  apiSecret: string = '';

  valid: boolean = false;
  errorMessages: string[] = [];
  step = 1;

  readonly usernameRules = [
    (v: string) =>
      !!v ||
      this.$t(
        'create_account.select_credentials.validation.non_empty_username'
      ),
    (v: string) =>
      (v && /^[0-9a-zA-Z_.-]+$/.test(v)) ||
      this.$t('create_account.select_credentials.validation.valid_username')
  ];

  readonly passwordRules = [
    (v: string) =>
      !!v ||
      this.$t('create_account.select_credentials.validation.non_empty_password')
  ];
  readonly passwordConfirmRules = [
    (v: string) =>
      !!v ||
      this.$t(
        'create_account.select_credentials.validation.non_empty_password_confirmation'
      )
  ];

  private updateConfirmationError() {
    if (this.errorMessages.length > 0) {
      return;
    }
    this.errorMessages.push(
      this.$t(
        'create_account.select_credentials.validation.password_confirmation_missmatch'
      ).toString()
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

  @Emit('error:clear')
  errorClear() {}

  back() {
    this.step = 1;
    if (this.error) {
      this.errorClear();
    }
  }
}
</script>

<style scoped lang="scss">
.create-account {
  &__header {
    padding: 12px;
  }

  &__analytics {
    &__content {
      background-color: #f8f8f8 !important;
    }
  }

  ::v-deep {
    .v-stepper {
      box-shadow: none !important;
      -webkit-box-shadow: none !important;

      &__header {
        box-shadow: none !important;
        -webkit-box-shadow: none !important;
      }

      &__content {
        padding: 12px !important;
      }
    }
  }
}
</style>
