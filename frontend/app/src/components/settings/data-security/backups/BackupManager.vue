<template>
  <card outlined-body>
    <template #title>{{ $t('backup_manager.title') }}</template>
    <template #hint>
      <v-row align="start">
        <v-col :class="$style.label" cols="auto">
          {{ $t('backup_manager.directory') }}
        </v-col>
        <v-col>{{ directory }}</v-col>
      </v-row>
      <v-row align="start">
        <v-col :class="$style.label" cols="auto">
          {{ $t('backup_manager.userdb') }}
        </v-col>
        <v-col>
          <v-row>
            {{
              $t('backup_manager.userdb_version', { version: userDb.version })
            }}
          </v-row>
          <v-row>
            {{ $t('backup_manager.userdb_size', { size: userDb.size }) }}
          </v-row>
        </v-col>
      </v-row>
      <v-row align="start">
        <v-col :class="$style.label" cols="auto">
          {{ $t('backup_manager.globaldb') }}
        </v-col>
        <v-col>
          <v-row>
            {{
              $t('backup_manager.globaldb_schema', { schema: globalDb.schema })
            }}
          </v-row>
          <v-row>
            {{
              $t('backup_manager.globaldb_assets', { schema: globalDb.assets })
            }}
          </v-row>
        </v-col>
      </v-row>
    </template>
    <database-backups :loading="loading" :items="backups" @remove="remove" />
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
import i18n from '@/i18n';
import { DatabaseInfo, UserDbBackup } from '@/services/backup/types';
import { api } from '@/services/rotkehlchen-api';
import { userNotify } from '@/store/notifications/utils';
import { size } from '@/utils/data';
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

    const directory = computed(() => {
      const info = backupInfo.value;
      if (!info) {
        return '';
      }
      const { filepath } = info.userdb.info;

      let index = filepath.lastIndexOf('/');
      let separatorLength = 1;
      if (index === -1) {
        index = filepath.lastIndexOf('\\');
        separatorLength = 2;
      }

      return filepath.substr(0, index + separatorLength);
    });

    const userDb = computed(() => {
      const info = backupInfo.value;
      return {
        size: info ? size(info.userdb.info.size) : '0',
        version: info ? info.userdb.info.version : '0'
      };
    });

    const globalDb = computed(() => {
      const info = backupInfo.value;
      return {
        schema: info ? info.globaldb.globaldbSchemaVersion : '0',
        assets: info ? info.globaldb.globaldbAssetsVersion : '0'
      };
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

    const remove = async (db: UserDbBackup) => {
      const file = `${db.time}_rotkehlchen_db_v${db.version}.backup`;
      const filepath = `${directory.value}${file}`;
      try {
        await api.backups.deleteBackup(filepath);
        if (backupInfo.value) {
          const info: DatabaseInfo = { ...backupInfo.value };
          const index = info.userdb.backups.findIndex(
            ({ size, time, version }) =>
              version === db.version && time === db.time && size === db.size
          );
          info.userdb.backups.splice(index, 1);
          backupInfo.value = info;
        }
      } catch (e: any) {
        logger.error(e);
        await userNotify({
          display: true,
          title: i18n.t('database_backups.delete_error.title').toString(),
          message: i18n
            .t('database_backups.delete_error.message', {
              file,
              message: e.message
            })
            .toString()
        });
      }
    };

    return { backups, directory, userDb, globalDb, loading, error, remove };
  }
});
export default BackupManager;
</script>

<style module lang="scss">
.label {
  font-weight: 600;
  margin-right: 8px;
  min-width: 150px;
}
</style>
