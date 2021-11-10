<template>
  <div class="user-security-settings">
    <change-password />
    <asset-update />
    <backup-manager class="mt-8" />
    <restore-assets-database />
    <data-management class="mt-8" />
    <oracle-cache-management class="mt-8" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import BackupManager from '@/components/settings/data-security/backups/BackupManager.vue';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import DataManagement from '@/components/settings/data-security/DataManagement.vue';
import OracleCacheManagement from '@/components/settings/data-security/OracleCacheManagement.vue';
import RestoreAssetsDatabase from '@/components/settings/data-security/RestoreAssetsDatabase.vue';
import AssetUpdate from '@/components/status/update/AssetUpdate.vue';

const UserSecuritySettings = defineComponent({
  name: 'UserSecuritySettings',
  components: {
    BackupManager,
    AssetUpdate,
    RestoreAssetsDatabase,
    OracleCacheManagement,
    ChangePassword,
    DataManagement
  }
});
export default UserSecuritySettings;
</script>
