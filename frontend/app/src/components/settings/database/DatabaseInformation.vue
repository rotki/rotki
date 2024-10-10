<script setup lang="ts">
import type { DatabaseInfo } from '@/types/backup';

const backupInfo = ref<DatabaseInfo>();
const loading = ref(false);

const { t } = useI18n();
const { notify } = useNotificationsStore();

const directory = computed(() => {
  const info = get(backupInfo);
  if (!info)
    return '';

  const { filepath } = info.userdb.info;

  let index = filepath.lastIndexOf('/');
  if (index === -1)
    index = filepath.lastIndexOf('\\');

  return filepath.slice(0, index + 1);
});

const userDb = computed(() => {
  const info = get(backupInfo);
  return {
    size: info ? size(info.userdb.info.size) : '0',
    version: info ? info.userdb.info.version.toString() : '0',
  };
});

const globalDb = computed(() => {
  const info = get(backupInfo);
  return {
    schema: info ? info.globaldb.globaldbSchemaVersion.toString() : '0',
    assets: info ? info.globaldb.globaldbAssetsVersion.toString() : '0',
  };
});

const { info } = useBackupApi();

async function loadInfo() {
  try {
    set(loading, true);
    set(backupInfo, await info());
  }
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      title: t('database_backups.load_error.title'),
      message: t('database_backups.load_error.message', {
        message: error.message,
      }),
    });
  }
  finally {
    set(loading, false);
  }
}

onMounted(loadInfo);
</script>

<template>
  <DatabaseInfoDisplay
    :directory="directory"
    :global-db="globalDb"
    :user-db="userDb"
    :loading="loading"
    @refresh="loadInfo()"
  />
</template>
