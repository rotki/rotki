<template>
  <card outlined-body>
    <template #title>{{ $t('backup_manager.title') }}</template>
    <database-backups :items="backups" />
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  ref
} from '@vue/composition-api';
import DatabaseBackups from '@/components/settings/data-security/backups/DatabaseBackups.vue';
import { DatabaseInfo } from '@/services/backup/types';
import { api } from '@/services/rotkehlchen-api';
import { logger } from '@/utils/logging';

const BackupManager = defineComponent({
  name: 'BackupManager',
  components: {
    DatabaseBackups
  },
  setup() {
    const backupInfo = ref<DatabaseInfo | null>();
    const loading = ref(false);
    const error = ref('');

    const backups = computed(() => {
      return backupInfo?.value?.userdb?.backups ?? [];
    });
    const loadInfo = async () => {
      try {
        loading.value = true;
        backupInfo.value = await api.backups.info();
      } catch (e: any) {
        logger.error(e);
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    };
    onMounted(loadInfo);

    return { backups, error };
  }
});
export default BackupManager;
</script>
