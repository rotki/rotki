<template>
  <div>
    <v-row align="start">
      <v-col :class="$style.label" cols="auto">
        {{ $t('backup_manager.directory') }}
      </v-col>
      <v-col>{{ directory }}</v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-row align="start">
          <v-col :class="$style.label" cols="auto">
            {{ $t('backup_manager.userdb') }}
          </v-col>
          <v-col>
            <div>
              {{
                $t('backup_manager.userdb_version', { version: userDb.version })
              }}
            </div>
            <div>
              {{ $t('backup_manager.userdb_size', { size: userDb.size }) }}
            </div>
          </v-col>
        </v-row>
      </v-col>
      <v-col>
        <v-row align="start">
          <v-col :class="$style.label" cols="auto">
            {{ $t('backup_manager.globaldb') }}
          </v-col>
          <v-col>
            <div>
              {{
                $t('backup_manager.globaldb_schema', {
                  schema: globalDb.schema
                })
              }}
            </div>
            <div>
              {{
                $t('backup_manager.globaldb_assets', {
                  assets: globalDb.assets
                })
              }}
            </div>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </div>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';

type UserDbInfo = {
  version: string;
  size: string;
};

type GlobalDbInfo = {
  schema: string;
  assets: string;
};

export default defineComponent({
  name: 'DatabaseInfoDisplay',
  props: {
    directory: {
      required: true,
      type: String
    },
    globalDb: {
      required: true,
      type: Object as PropType<GlobalDbInfo>
    },
    userDb: {
      required: true,
      type: Object as PropType<UserDbInfo>
    }
  }
});
</script>
<style module lang="scss">
.label {
  font-weight: 600;
  margin-right: 8px;
  min-width: 150px;
}
</style>
