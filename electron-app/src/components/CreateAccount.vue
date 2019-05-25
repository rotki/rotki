<template>
  <v-dialog v-model="displayed" persistent max-width="450">
    <v-card>
      <v-toolbar card>
        <v-toolbar-title>Create New Account</v-toolbar-title>
      </v-toolbar>
      <v-card-text>
        <v-form ref="form" v-model="valid">
          <v-text-field
            id="username_entry"
            v-model="username"
            label="Username"
            prepend-icon="fa-user"
            :rules="usernameRules"
            required
          ></v-text-field>
          <v-text-field
            id="password_entry"
            v-model="password"
            label="Password"
            prepend-icon="fa-lock"
            :rules="passwordRules"
            type="password"
            required
          ></v-text-field>
          <v-text-field
            id="repeat_password_entry"
            v-model="passwordConfirm"
            prepend-icon="fa-repeat"
            :rules="passwordConfirmRules"
            label="Repeat Password"
            type="password"
            required
          >
          </v-text-field>
          <v-text-field
            id="api_key_entry"
            v-model="apiKey"
            prepend-icon="fa-key"
            label="API KEY"
            persistent-hint
            hint="Optional: Only for premium users"
          >
          </v-text-field>
          <v-text-field
            id="api_secret_entry"
            v-model="apiSecret"
            persistent-hint
            prepend-icon="fa-user-secret"
            hint="Optional: Only for premium users"
            label="API SECRET"
          ></v-text-field>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-btn depressed color="primary" :disabled="!valid" @click="confirm()">
          Create
        </v-btn>
        <v-btn depressed color="primary" @click="cancel()">
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { AccountData } from '@/typing/types';

@Component({})
export default class CreateAccount extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  username: string = '';
  password: string = '';
  passwordConfirm: string = '';
  apiKey: string = '';
  apiSecret: string = '';

  valid: boolean = false;

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

  @Watch('displayed')
  onDisplayChange() {
    this.username = '';
    this.password = '';
    this.passwordConfirm = '';
    this.apiKey = '';
    this.apiSecret = '';

    (this.$refs.form as any).reset();
  }

  confirm() {
    const account: AccountData = {
      username: this.username,
      password: this.password,
      apiKey: this.apiKey,
      apiSecret: this.apiSecret
    };
    this.$emit('confirm', account);
  }

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
