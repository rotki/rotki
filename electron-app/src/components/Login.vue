<template>
  <v-dialog v-model="displayed" persistent max-width="450">
    <v-card>
      <v-card-title>Sign In</v-card-title>
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
            @keypress.enter="login()"
          ></v-text-field>
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-btn depressed color="primary" :disabled="!valid" @click="login()">
          Sign In
        </v-btn>
        <v-btn depressed color="primary" @click="newAccount()">
          Create New Account
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { Credentials } from '@/typing/types';

@Component({})
export default class Login extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Watch('displayed')
  onDisplayChange() {
    this.username = '';
    this.password = '';
    (this.$refs.form as any).reset();
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

  login() {
    const credentials: Credentials = {
      username: this.username,
      password: this.password
    };
    this.$emit('login', credentials);
  }

  @Emit()
  newAccount() {}
}
</script>

<style scoped></style>
