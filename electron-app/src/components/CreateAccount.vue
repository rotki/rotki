<template>
  <v-dialog
    v-model="displayed"
    persistent
    max-width="450"
    class="create-account"
  >
    <v-card>
      <v-card-title>Create New Account</v-card-title>
      <v-card-text>
        <v-form ref="form" v-model="valid">
          <v-text-field
            v-model="username"
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
            :rules="passwordConfirmRules"
            :disabled="loading"
            label="Repeat Password"
            type="password"
            required
          >
          </v-text-field>
        </v-form>
      </v-card-text>
      <v-card-actions>
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
        <v-btn
          class="create-account__buttons__cancel"
          depressed
          color="primary"
          :disabled="loading"
          @click="cancel()"
        >
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { Credentials } from '@/typing/types';

@Component({})
export default class CreateAccount extends Vue {
  @Prop({ required: true })
  displayed!: boolean;

  @Prop({ required: true, type: Boolean, default: false })
  loading!: boolean;

  username: string = '';
  password: string = '';
  passwordConfirm: string = '';

  valid: boolean = false;

  readonly usernameRules = [
    (v: string) => !!v || 'Please provide a user name',
    (v: string) =>
      (v && /^[0-9a-zA-Z_.-]+$/.test(v)) ||
      'A username must contain only alphanumeric characters and have no spaces'
  ];

  readonly passwordRules = [(v: string) => !!v || 'Please provide a password'];
  readonly passwordConfirmRules = [
    (v: string) => !!v || 'Please provide a password confirmation',
    (v: string) =>
      v == this.password ||
      'The password confirmation does not match the provided password'
  ];

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
    const credentials: Credentials = {
      username: this.username,
      password: this.password
    };
    this.$emit('confirm', credentials);
  }

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
