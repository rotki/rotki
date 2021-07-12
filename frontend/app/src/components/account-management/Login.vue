<template>
  <div v-if="displayed" class="login">
    <v-card-title>
      {{ $t('login.title') }}
    </v-card-title>
    <v-card-text>
      <v-form ref="form" v-model="valid">
        <v-text-field
          ref="username"
          v-model="username"
          class="login__fields__username"
          color="secondary"
          :label="$t('login.label_username')"
          prepend-icon="mdi-account"
          :rules="usernameRules"
          :disabled="loading || !!syncConflict.message || customBackendDisplay"
          required
          @keypress.enter="login()"
        />

        <revealable-input
          ref="password"
          v-model="password"
          :rules="passwordRules"
          :disabled="loading || !!syncConflict.message || customBackendDisplay"
          type="password"
          required
          class="login__fields__password"
          color="secondary"
          :label="$t('login.label_password')"
          prepend-icon="mdi-lock"
          @keypress.enter="login()"
        />

        <v-row no-gutters align="center">
          <v-col>
            <v-checkbox
              v-model="rememberUser"
              :disabled="customBackendDisplay"
              color="primary"
              :label="$t('login.remember_me')"
            />
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  icon
                  :color="serverColor"
                  v-bind="attrs"
                  v-on="on"
                  @click="customBackendDisplay = !customBackendDisplay"
                >
                  <v-icon>mdi-server</v-icon>
                </v-btn>
              </template>
              <span v-text="$t('login.custom_backend.tooltip')" />
            </v-tooltip>
          </v-col>
        </v-row>

        <transition v-if="customBackendDisplay" name="bounce">
          <div>
            <v-divider />
            <v-row no-gutters class="mt-4" align="center">
              <v-col>
                <v-text-field
                  v-model="customBackendUrl"
                  prepend-icon="mdi-server"
                  :rules="customBackendRules"
                  :disabled="customBackendSaved"
                  :label="$t('login.custom_backend.label')"
                  :placeholder="$t('login.custom_backend.placeholder')"
                  :hint="$t('login.custom_backend.hint')"
                  @keypress.enter="saveCustomBackend"
                />
              </v-col>
              <v-col cols="auto">
                <v-btn
                  v-if="!customBackendSaved"
                  class="ms-2"
                  icon
                  @click="saveCustomBackend()"
                >
                  <v-icon>mdi-content-save</v-icon>
                </v-btn>
                <v-btn v-else icon @click="clearCustomBackend()">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </v-col>
            </v-row>
            <v-row no-gutters>
              <v-col>
                <v-checkbox
                  v-model="customBackendSessionOnly"
                  :disabled="customBackendSaved"
                  :label="$t('login.custom_backend.session_only')"
                />
              </v-col>
            </v-row>
          </div>
        </transition>

        <transition name="bounce">
          <v-alert
            v-if="!!syncConflict.message"
            class="login__sync-error"
            text
            prominent
            outlined
            type="info"
            icon="mdi-cloud-download"
          >
            <div class="login__sync-error__header text-h6">
              {{ $t('login.sync_error.title') }}
            </div>
            <div class="login__sync-error__body mt-2">
              <div>
                <div>{{ syncConflict.message }}</div>
                <ul class="mt-2">
                  <li>
                    <i18n path="login.sync_error.local_modified">
                      <div class="font-weight-medium">
                        <date-display :timestamp="localLastModified" />
                      </div>
                    </i18n>
                  </li>
                  <li class="mt-2">
                    <i18n path="login.sync_error.remote_modified">
                      <div class="font-weight-medium">
                        <date-display :timestamp="remoteLastModified" />
                      </div>
                    </i18n>
                  </li>
                  <li class="mt-2">
                    <i18n path="login.sync_error.local_size">
                      <div class="font-weight-medium">
                        {{ localSize }}
                      </div>
                    </i18n>
                  </li>
                  <li class="mt-2">
                    <i18n path="login.sync_error.remote_size">
                      <div class="font-weight-medium">
                        {{ remoteSize }}
                      </div>
                    </i18n>
                  </li>
                </ul>
              </div>
              <div class="mt-2">{{ $t('login.sync_error.question') }}</div>
            </div>

            <v-row no-gutters justify="end" class="mt-2">
              <v-col cols="3" class="shrink">
                <v-btn color="error" depressed @click="login('no')">
                  {{ $t('login.sync_error.button_no') }}
                </v-btn>
              </v-col>
              <v-col cols="3" class="shrink">
                <v-btn color="success" depressed @click="login('yes')">
                  {{ $t('login.sync_error.button_yes') }}
                </v-btn>
              </v-col>
            </v-row>
          </v-alert>
        </transition>
        <transition name="bounce">
          <v-alert
            v-if="errors.length > 0"
            text
            outlined
            type="error"
            icon="mdi-alert-circle-outline"
          >
            <v-row>
              <v-col class="grow">
                <span v-for="(error, i) in errors" :key="i" v-text="error" />
              </v-col>
              <v-col class="shrink">
                <v-btn
                  v-if="isLoggedInError"
                  depressed
                  color="primary"
                  @click="logout"
                >
                  {{ $t('login.logout') }}
                </v-btn>
              </v-col>
            </v-row>
          </v-alert>
        </transition>
      </v-form>
    </v-card-text>
    <v-card-actions class="login__actions d-block">
      <span>
        <v-btn
          class="login__button__sign-in"
          depressed
          color="primary"
          :disabled="
            !valid || loading || !!syncConflict.message || customBackendDisplay
          "
          :loading="loading"
          @click="login()"
        >
          {{ $t('login.button_signin') }}
        </v-btn>
      </span>
      <v-divider class="my-3" />
      <span class="login__actions__footer">
        <a
          class="login__button__new-account font-weight-bold secondary--text"
          @click="newAccount()"
        >
          {{ $t('login.button_new_account') }}
        </a>
      </span>
    </v-card-actions>
  </div>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import {
  deleteBackendUrl,
  getBackendUrl,
  saveBackendUrl
} from '@/components/account-management/utils';
import RevealableInput from '@/components/inputs/RevealableInput.vue';
import { SyncConflict } from '@/store/session/types';
import { ActionStatus } from '@/store/types';
import { Credentials, SyncApproval } from '@/typing/types';

const KEY_REMEMBER = 'rotki.remember';
const KEY_USERNAME = 'rotki.username';

@Component({
  components: { RevealableInput },
  methods: {
    ...mapActions('session', ['logoutRemoteSession'])
  }
})
export default class Login extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Prop({ required: true, type: Boolean })
  loading!: boolean;

  @Prop({ required: true })
  syncConflict!: SyncConflict;

  @Prop({ required: false, type: Array, default: () => [] })
  errors!: string[];

  logoutRemoteSession!: () => Promise<ActionStatus>;

  @Watch('username')
  onUsernameChange() {
    this.touched();
  }

  @Watch('password')
  onPasswordChange() {
    this.touched();
  }

  get isLoggedInError(): boolean {
    return !!this.errors.find(error => error.includes('is already logged in'));
  }

  async logout() {
    const { success } = await this.logoutRemoteSession();
    if (success) {
      this.touched();
    }
  }

  get localLastModified(): number {
    const payload = this.syncConflict.payload;
    return payload?.localLastModified ?? 0;
  }

  get remoteLastModified(): number {
    const payload = this.syncConflict.payload;
    return payload?.remoteLastModified ?? 0;
  }

  get localSize(): string {
    return this.syncConflict.payload?.localSize ?? '';
  }

  get remoteSize(): string {
    return this.syncConflict.payload?.remoteSize ?? '';
  }

  get serverColor(): string | null {
    if (this.customBackendSessionOnly) {
      return 'primary';
    } else if (this.customBackendSaved) {
      return 'success';
    }

    return null;
  }

  @Watch('displayed')
  onDisplayChange() {
    this.username = '';
    this.password = '';
    const form = this.$refs.form as any;

    if (form) {
      form.reset();
    }
    this.loadSettings();
    this.updateFocus();
  }

  getRef(prop: 'password' | 'username'): Promise<any> {
    return new Promise<any>(resolve => {
      let count = 0;
      const interval = setInterval(() => {
        count++;
        if (count > 10) {
          clearInterval(interval);
          return;
        }

        const $ref = this.$refs[prop];
        if (!$ref) {
          return;
        }
        clearInterval(interval);
        resolve($ref);
      }, 500);
    });
  }

  private updateFocus() {
    const ref = this.getRef(this.username ? 'password' : 'username');
    ref.then(value => {
      this.focusElement(value);
    });
  }

  username: string = '';
  password: string = '';
  rememberUser: boolean = false;
  customBackendDisplay: boolean = false;
  customBackendUrl: string = '';
  customBackendSessionOnly: boolean = false;
  customBackendSaved: boolean = false;

  valid = false;

  readonly customBackendRules = [
    (v: string) =>
      !!v || this.$t('login.custom_backend.validation.non_empty').toString(),
    (v: string) =>
      (v &&
        v.length < 300 &&
        /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}(\.[a-zA-Z0-9()]{1,6})?\b([-a-zA-Z0-9()@:%_+.~#?&/=]*)$/.test(
          v
        )) ||
      this.$t('login.custom_backend.validation.url')
  ];

  readonly usernameRules = [
    (v: string) => !!v || this.$t('login.validation.non_empty_username'),
    (v: string) =>
      (v && /^[0-9a-zA-Z_.-]+$/.test(v)) ||
      this.$t('login.validation.valid_username')
  ];

  readonly passwordRules = [
    (v: string) => !!v || this.$t('login.validation.non_empty_password')
  ];

  mounted() {
    this.loadSettings();
    this.updateFocus();
  }

  private focusElement(element: any) {
    requestAnimationFrame(() => {
      const input = element.$el.querySelector(
        'input:not([type=hidden])'
      ) as HTMLInputElement;
      input.focus();
    });
  }

  private saveCustomBackend() {
    saveBackendUrl({
      url: this.customBackendUrl,
      sessionOnly: this.customBackendSessionOnly
    });
    this.backendChanged(this.customBackendUrl);
    this.customBackendSaved = true;
    this.customBackendDisplay = false;
  }

  private clearCustomBackend() {
    this.customBackendUrl = '';
    this.customBackendSessionOnly = false;
    deleteBackendUrl();
    this.backendChanged(null);
    this.customBackendSaved = false;
    this.customBackendDisplay = false;
  }

  private loadSettings() {
    this.rememberUser = !!localStorage.getItem(KEY_REMEMBER);
    this.username = localStorage.getItem(KEY_USERNAME) ?? '';
    const { sessionOnly, url } = getBackendUrl();
    this.customBackendUrl = url;
    this.customBackendSessionOnly = sessionOnly;
    this.customBackendSaved = !!url;
  }

  @Watch('rememberUser')
  onRememberChange(remember: boolean, previous: boolean) {
    if (remember === previous) {
      return;
    }

    if (!remember) {
      localStorage.removeItem(KEY_REMEMBER);
      localStorage.removeItem(KEY_USERNAME);
    } else {
      localStorage.setItem(KEY_REMEMBER, `${true}`);
    }
  }

  login(syncApproval: SyncApproval = 'unknown') {
    const credentials: Credentials = {
      username: this.username,
      password: this.password,
      syncApproval
    };
    this.$emit('login', credentials);
    if (this.rememberUser) {
      localStorage.setItem(KEY_USERNAME, this.username);
    }
  }

  @Emit()
  newAccount() {}

  @Emit()
  touched() {}

  @Emit()
  backendChanged(_url: string | null) {}
}
</script>

<style scoped lang="scss">
.login {
  &__actions {
    &__footer {
      font-size: 0.9em;
    }

    span,
    button {
      display: block;
      width: 100%;
      text-align: center;
    }
  }

  &__sync-error {
    &__body {
      margin-top: 5px;
      margin-bottom: 8px;
    }
  }
}

.bounce-enter-active {
  animation: bounce-in 0.5s;
}

.bounce-leave-active {
  animation: bounce-in 0.5s reverse;
}

@keyframes bounce-in {
  0% {
    transform: scale(0);
  }

  50% {
    transform: scale(1.1);
  }

  100% {
    transform: scale(1);
  }
}
</style>
