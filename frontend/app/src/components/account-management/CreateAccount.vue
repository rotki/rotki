<template>
  <div v-if="displayed" class="create-account">
    <div class="text-h6 text--primary create-account__header">
      {{ $t('create_account.title') }}
    </div>
    <v-stepper v-model="step">
      <v-stepper-header>
        <v-stepper-step step="1" :complete="step > 1">
          <span v-if="step === 1">
            {{ $t('create_account.premium.title') }}
          </span>
        </v-stepper-step>
        <v-divider />
        <v-stepper-step step="2" :complete="step > 2">
          <span v-if="step === 2">
            {{ $t('create_account.select_credentials.title') }}
          </span>
        </v-stepper-step>
        <v-divider />
        <v-stepper-step step="3">
          <span v-if="step === 3">
            {{ $t('create_account.usage_analytics.title') }}
          </span>
        </v-stepper-step>
      </v-stepper-header>
      <v-stepper-items>
        <v-stepper-content step="1">
          <v-card-text>
            <v-form v-model="premiumFormValid">
              <v-alert text color="primary">
                <i18n tag="div" path="create_account.premium.premium_question">
                  <template #premiumLink>
                    <b>
                      <external-link url="https://rotki.com/products">
                        {{ $t('create_account.premium.premium_link_text') }}
                      </external-link>
                    </b>
                  </template>
                </i18n>
                <div class="d-flex mt-4 justify-center">
                  <v-btn
                    depressed
                    rounded
                    small
                    :outlined="premiumEnabled"
                    color="primary"
                    @click="
                      premiumEnabled = false;
                      syncDatabase = false;
                    "
                  >
                    <v-icon small class="mr-2">mdi-close</v-icon>
                    <span>
                      {{ $t('create_account.premium.button_premium_reject') }}
                    </span>
                  </v-btn>
                  <v-btn
                    depressed
                    rounded
                    small
                    :outlined="!premiumEnabled"
                    color="primary"
                    class="ml-2"
                    @click="premiumEnabled = true"
                  >
                    <v-icon small class="mr-2"> mdi-check</v-icon>
                    <span>
                      {{ $t('create_account.premium.button_premium_approve') }}
                    </span>
                  </v-btn>
                </div>
              </v-alert>

              <premium-credentials
                :enabled="premiumEnabled"
                :api-secret="apiSecret"
                :api-key="apiKey"
                :loading="loading"
                :sync-database="syncDatabase"
                @update:api-key="apiKey = $event"
                @update:api-secret="apiSecret = $event"
                @update:sync-database="syncDatabase = $event"
              />
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              class="create-account__button__cancel"
              depressed
              outlined
              color="primary"
              :disabled="loading || newUser"
              @click="cancel()"
            >
              {{ $t('create_account.premium.button_cancel') }}
            </v-btn>
            <v-btn
              class="create-account__premium__button__continue"
              depressed
              color="primary"
              :disabled="!premiumFormValid"
              :loading="loading"
              data-cy="create-account__premium__button__continue"
              @click="step = 2"
            >
              {{ $t('create_account.premium.button_continue') }}
            </v-btn>
          </v-card-actions>
        </v-stepper-content>
        <v-stepper-content step="2">
          <v-card-text>
            <v-form ref="form" v-model="credentialsFormValid">
              <v-text-field
                v-model="username"
                outlined
                autofocus
                single-line
                class="create-account__fields__username"
                :label="$t('create_account.select_credentials.label_username')"
                prepend-inner-icon="mdi-account"
                :rules="usernameRules"
                :disabled="loading"
                required
              />
              <v-alert
                v-if="syncDatabase"
                text
                class="mt-2 create-account__password-sync-requirement"
                outlined
                color="deep-orange"
                icon="mdi-information"
              >
                {{
                  $t(
                    'create_account.select_credentials.password_sync_requirement'
                  )
                }}
              </v-alert>
              <revealable-input
                v-model="password"
                outlined
                class="create-account__fields__password"
                :label="$t('create_account.select_credentials.label_password')"
                prepend-icon="mdi-lock"
                :rules="passwordRules"
                :disabled="loading"
                required
              />
              <revealable-input
                v-model="passwordConfirm"
                outlined
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
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn
              color="primary"
              class="create-account__credentials__button__back"
              depressed
              :disabled="loading"
              outlined
              @click="back"
            >
              {{ $t('create_account.select_credentials.button_back') }}
            </v-btn>
            <v-btn
              class="create-account__credentials__button__continue"
              depressed
              color="primary"
              :disabled="!credentialsFormValid || loading || !userPrompted"
              :loading="loading"
              @click="step = 3"
            >
              {{ $t('create_account.select_credentials.button_continue') }}
            </v-btn>
          </v-card-actions>
        </v-stepper-content>
        <v-stepper-content step="3">
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
                class="
                  mx-auto
                  text-justify text-body-2
                  create-account__analytics__content
                "
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
                class="create-account__analytics__button__back"
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
                class="create-account__analytics__button__confirm"
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
import { mapState } from 'vuex';
import PremiumCredentials from '@/components/account-management/PremiumCredentials.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { CreateAccountPayload } from '@/types/login';

@Component({
  components: { ExternalLink, RevealableInput, PremiumCredentials },
  computed: {
    ...mapState(['newUser'])
  }
})
export default class CreateAccount extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Prop({ required: true, type: Boolean, default: false })
  loading!: boolean;

  @Prop({ required: false, type: String, default: '' })
  error!: string;

  newUser!: boolean;
  username: string = '';
  password: string = '';
  passwordConfirm: string = '';

  premiumEnabled: boolean = false;
  userPrompted: boolean = false;

  submitUsageAnalytics: boolean = true;
  apiKey: string = '';
  apiSecret: string = '';
  syncDatabase: boolean = false;

  premiumFormValid: boolean = true;
  credentialsFormValid: boolean = false;
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
    const payload: CreateAccountPayload = {
      credentials: {
        username: this.username,
        password: this.password
      }
    };

    if (this.premiumEnabled) {
      payload.premiumSetup = {
        apiKey: this.apiKey,
        apiSecret: this.apiSecret,
        submitUsageAnalytics: this.submitUsageAnalytics,
        syncDatabase: this.syncDatabase
      };
    }

    this.$emit('confirm', payload);
  }

  @Emit()
  cancel() {}

  @Emit('error:clear')
  errorClear() {}

  back() {
    this.step = Math.max(this.step - 1, 1);
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

  &__password-sync-requirement {
    font-weight: bold;
    font-size: 0.8rem;
    line-height: 1rem;
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
