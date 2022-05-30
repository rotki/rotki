<template>
  <div>
    <change-password />
    <asset-update />
    <backup-manager class="mt-8" />
    <data-management class="mt-8" />
    <oracle-cache-management class="mt-8" />
    <manage-custom-assets class="mt-8" />
    <restore-assets-database />
  </div>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import BackupManager from '@/components/settings/data-security/backups/BackupManager.vue';
import ManageCustomAssets from '@/components/settings/data-security/backups/ManageCustomAssets.vue';
import ChangePassword from '@/components/settings/data-security/ChangePassword.vue';
import DataManagement from '@/components/settings/data-security/DataManagement.vue';
import OracleCacheManagement from '@/components/settings/data-security/OracleCacheManagement.vue';
import RestoreAssetsDatabase from '@/components/settings/data-security/RestoreAssetsDatabase.vue';
import AssetUpdate from '@/components/status/update/AssetUpdate.vue';

export default defineComponent({
  name: 'UserSecuritySettings',
  components: {
    ManageCustomAssets,
    BackupManager,
    AssetUpdate,
    RestoreAssetsDatabase,
    OracleCacheManagement,
    ChangePassword,
    DataManagement
  }
});
</script>
