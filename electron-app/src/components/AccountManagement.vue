<template>
  <div>
    <login
      :displayed="!logged && !accountCreation"
      :loading="loading"
      @login="login($event)"
      @new-account="accountCreation = true"
    ></login>
    <create-account
      :loading="loading"
      :displayed="!logged && accountCreation"
      @cancel="accountCreation = false"
      @confirm="createAccount($event)"
    ></create-account>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import Login from './Login.vue';
import CreateAccount from './CreateAccount.vue';
import { Credentials } from '@/typing/types';
import { UnlockPayload } from '@/store/session/actions';

const { mapState } = createNamespacedHelpers('session');

@Component({
  components: {
    Login,
    CreateAccount
  },
  computed: {
    ...mapState(['newAccount'])
  }
})
export default class AccountManagement extends Vue {
  accountCreation: boolean = false;
  newAccount!: boolean;
  loading: boolean = false;

  @Prop({ required: true, type: Boolean })
  logged!: boolean;

  async login(credentials: Credentials) {
    const { username, password } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username: username,
      password: password
    } as UnlockPayload);
    this.loading = false;
  }

  async createAccount(credentials: Credentials) {
    const { username, password } = credentials;
    this.loading = true;
    await this.$store.dispatch('session/unlock', {
      username: username,
      password: password,
      create: true,
      syncApproval: 'unknown'
    } as UnlockPayload);
    this.loading = false;
  }
}
</script>

<style scoped></style>
