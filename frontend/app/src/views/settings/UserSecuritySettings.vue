<template>
  <v-container class="user-security-settings">
    <change-password />
    <asset-update />
    <data-management class="mt-8" />
    <oracle-cache-management class="mt-8" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import DataManagement from '@/components/settings/data-security/DataManagement.vue';
import OracleCacheManagement from '@/components/settings/data-security/OracleCacheManagement.vue';
import AssetUpdate from '@/components/status/update/AssetUpdate.vue';

@Component({
  components: {
    AssetUpdate,
    OracleCacheManagement,
    ChangePassword,
    DataManagement
  }
})
export default class UserSecuritySettings extends Vue {}
</script>
