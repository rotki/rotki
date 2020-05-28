<template>
  <div v-if="displayed" class="login">
    <v-card-title>Sign In</v-card-title>
    <v-card-text>
      <v-form ref="form" v-model="valid">
        <v-text-field
          v-model="username"
          autofocus
          class="login__fields__username"
          label="Username"
          prepend-icon="fa-user"
          :rules="usernameRules"
          :disabled="loading || !!syncConflict"
          required
        ></v-text-field>
        <v-text-field
          v-model="password"
          class="login__fields__password"
          label="Password"
          prepend-icon="fa-lock"
          :rules="passwordRules"
          :disabled="loading || !!syncConflict"
          type="password"
          required
          @keypress.enter="login()"
        ></v-text-field>
        <transition name="bounce">
          <v-alert
            v-if="!!syncConflict"
            class="login__sync-error"
            text
            prominent
            outlined
            type="error"
            icon="fa-cloud-download"
          >
            <h3 class="login__sync-error__header">Sync Error</h3>
            <div class="login__sync-error__body">
              {{ syncConflict }}
            </div>

            <v-row no-gutters justify="end">
              <v-col cols="3" class="shrink">
                <v-btn color="error" depressed @click="login('no')">
                  No
                </v-btn>
              </v-col>
              <v-col cols="3" class="shrink">
                <v-btn color="success" depressed @click="login('yes')">
                  Yes
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
          :disabled="!valid || loading || !!syncConflict"
          :loading="loading"
          @click="login()"
        >
          Sign In
        </v-btn>
      </span>
      <v-divider class="my-3"></v-divider>
      <span style="font-size: 0.9em;">
        <a class="login__button__new-account" @click="newAccount()">
          Create New Account
        </a>
      </span>
    </v-card-actions>
  </div>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { Credentials, SyncApproval } from '@/typing/types';

@Component({})
export default class Login extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Prop({ required: true, type: Boolean })
  loading!: boolean;

  @Prop({ required: true })
  syncConflict!: string;

  @Watch('displayed')
  onDisplayChange() {
    this.username = '';
    this.password = '';
    const form = this.$refs.form as any;

    if (form) {
      form.reset();
    }
  }

  username: string = '';
  password: string = '';

  valid = false;

  readonly usernameRules = [
    (v: string) => !!v || 'Please provide a user name',
    (v: string) =>
      (v && /^[0-9a-zA-Z_.-]+$/.test(v)) ||
      'A username must contain only alphanumeric characters and have no spaces'
  ];

  readonly passwordRules = [(v: string) => !!v || 'Please provide a password'];

  login(syncApproval: SyncApproval = 'unknown') {
    const credentials: Credentials = {
      username: this.username,
      password: this.password,
      syncApproval
    };
    this.$emit('login', credentials);
  }

  @Emit()
  newAccount() {}
}
</script>

<style scoped lang="scss">
.login__sync-error__body {
  margin-top: 5px;
  margin-bottom: 8px;
}

.login__actions span,
.login__actions button {
  display: block;
  width: 100%;
  text-align: center;
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
