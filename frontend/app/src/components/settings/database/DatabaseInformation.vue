<script setup lang="ts">
import type { DatabaseInfo } from '@/types/backup';

interface UserDbInfo {
  version: string;
  size: string;
}

interface GlobalDbInfo {
  schema: string;
  assets: string;
}

const { t } = useI18n();

const backupInfo = ref<DatabaseInfo>();
const loading = ref(false);

const { notify } = useNotificationsStore();
const { info } = useBackupApi();

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

const userDb = computed<UserDbInfo>(() => {
  const info = get(backupInfo);
  return {
    size: info ? size(info.userdb.info.size) : '0',
    version: info ? info.userdb.info.version.toString() : '0',
  };
});

const globalDb = computed<GlobalDbInfo>(() => {
  const info = get(backupInfo);
  return {
    schema: info ? info.globaldb.globaldbSchemaVersion.toString() : '0',
    assets: info ? info.globaldb.globaldbAssetsVersion.toString() : '0',
  };
});

const userDetails = computed(() => [
  {
    value: get(directory),
    label: t('database_settings.database_info.labels.directory'),
    copiable: true,
  },
  {
    value: get(userDb).version,
    label: t('database_settings.database_info.labels.userdb_version'),
  },
  {
    value: get(userDb).size,
    label: t('database_settings.database_info.labels.userdb_size'),
  },
]);

const globalDetails = computed(() => [
  {
    value: get(globalDb).schema,
    label: t('database_settings.database_info.labels.globaldb_schema'),
  },
  {
    value: get(globalDb).assets,
    label: t('database_settings.database_info.labels.globaldb_assets'),
  },
]);

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

const [DefineRow, ReuseRow] = createReusableTemplate<{
  details: {
    label: string;
    value: string;
    copiable?: boolean;
  }[];
}>();

onMounted(loadInfo);
</script>

<template>
  <DefineRow #default="{ details }">
    <RuiCard
      outlined
      no-padding
    >
      <div
        v-for="(item, index) in details"
        :key="index"
        class="mx-4 py-4 [&:not(:last-child)]:border-b border-default"
        :class="{ '!py-2': item.copiable }"
      >
        <div class="flex gap-4 items-center">
          <span class="font-medium w-[9rem]">
            {{ item.label }}
          </span>
          <span class="flex-1 text-rui-text-secondary overflow-hidden flex items-center gap-2">
            <span
              :title="item.value"
              class="text-truncate overflow-hidden"
            >
              {{ item.value }}
            </span>
            <CopyButton
              v-if="item.copiable"
              :tooltip="item.value"
              :value="item.value"
            />
          </span>
        </div>
      </div>
    </RuiCard>
  </DefineRow>
  <SettingsItem>
    <template #title>
      {{ t('database_settings.database_info.labels.userdb') }}
    </template>
    <ReuseRow :details="userDetails" />
  </SettingsItem>
  <SettingsItem>
    <template #title>
      {{ t('database_settings.database_info.labels.globaldb') }}
    </template>
    <ReuseRow :details="globalDetails" />
  </SettingsItem>
</template>
