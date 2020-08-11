<template>
  <v-container class="user-security-settings">
    <change-password />
    <data-management class="mt-4" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import DataManagement from '@/components/settings/data-security/DataManagement.vue';

@Component({
  components: { ChangePassword, DataManagement }
})
export default class UserSecuritySettings extends Vue {}
</script>
