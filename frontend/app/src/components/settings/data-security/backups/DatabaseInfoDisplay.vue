<template>
  <card>
    <template #title>{{ t('database_info_display.title') }}</template>

    <v-row>
      <v-col>
        <v-row>
          <v-col class="text-h6">
            {{ t('database_info_display.userdb') }}
          </v-col>
        </v-row>
        <v-row align="start" no-gutters class="mt-2">
          <v-col :class="$style.label" cols="auto">
            {{ t('database_info_display.directory') }}
          </v-col>
          <v-col>{{ directory }}</v-col>
        </v-row>
        <v-row align="start" no-gutters>
          <v-col :class="$style.label" cols="auto">
            {{ t('database_info_display.userdb_version') }}
          </v-col>
          <v-col>{{ userDb.version }}</v-col>
        </v-row>
        <v-row align="start" no-gutters>
          <v-col :class="$style.label" cols="auto">
            {{ t('database_info_display.userdb_size') }}
          </v-col>
          <v-col>{{ userDb.size }}</v-col>
        </v-row>
      </v-col>
      <v-col>
        <v-row>
          <v-col class="text-h6">
            {{ t('database_info_display.globaldb') }}
          </v-col>
        </v-row>
        <v-row align="start" no-gutters class="mt-2">
          <v-col :class="$style.label" cols="auto">
            {{ t('database_info_display.globaldb_schema') }}
          </v-col>
          <v-col>{{ globalDb.schema }}</v-col>
        </v-row>
        <v-row align="start" no-gutters>
          <v-col :class="$style.label" cols="auto">
            {{ t('database_info_display.globaldb_assets') }}
          </v-col>
          <v-col>{{ globalDb.assets }}</v-col>
        </v-row>
      </v-col>
    </v-row>
  </card>
</template>
<script setup lang="ts">
import { PropType } from 'vue';

type UserDbInfo = {
  version: string;
  size: string;
};

type GlobalDbInfo = {
  schema: string;
  assets: string;
};

defineProps({
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
});

const { t } = useI18n();
</script>
<style module lang="scss">
.label {
  font-weight: 600;
  margin-right: 8px;
  min-width: 150px;
}
</style>
