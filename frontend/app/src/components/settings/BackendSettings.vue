<template>
  <card>
    <template #title>{{ $t('backend_settings.title') }}</template>
    <template #subtitle>{{ $t('backend_settings.subtitle') }}</template>

    <v-text-field
      v-model="dataDirectory"
      outlined
      :disabled="!!fileConfig.dataDirectory"
      :persistent-hint="!!fileConfig.dataDirectory"
      :hint="
        !!fileConfig.dataDirectory
          ? $t('backend_settings.config_file_disabled')
          : null
      "
      :label="$t('backend_settings.settings.data_directory.label')"
      readonly
      @click="selectDirectory"
    >
      <template #append>
        <v-btn icon @click="selectDirectory">
          <v-icon>mdi-folder</v-icon>
        </v-btn>
      </template>
    </v-text-field>

    <v-text-field
      v-model="logDirectory"
      :disabled="!!fileConfig.logDirectory"
      :persistent-hint="!!fileConfig.logDirectory"
      :hint="
        !!fileConfig.logDirectory
          ? $t('backend_settings.config_file_disabled')
          : null
      "
      outlined
      :label="$t('backend_settings.settings.log_directory.label')"
      readonly
      @click="selectDirectory"
    >
      <template #append>
        <v-btn icon @click="selectDirectory">
          <v-icon>mdi-folder</v-icon>
        </v-btn>
      </template>
    </v-text-field>

    <v-select
      v-model="loglevel"
      :items="levels"
      :disabled="!!fileConfig.loglevel"
      :label="$t('backend_settings.settings.log_level.label')"
      :persistent-hint="!!fileConfig.loglevel"
      :hint="
        !!fileConfig.loglevel
          ? $t('backend_settings.config_file_disabled')
          : null
      "
      outlined
    >
      <template #item="{ item }">
        <v-row align="center">
          <v-col cols="auto">
            <v-icon>{{ icon(item) }}</v-icon>
          </v-col>
          <v-col>{{ item.toLocaleLowerCase() }}</v-col>
        </v-row>
      </template>
      <template #selection="{ item }">
        <v-row align="center">
          <v-col cols="auto">
            <v-icon>{{ icon(item) }}</v-icon>
          </v-col>
          <v-col>{{ item.toLocaleLowerCase() }}</v-col>
        </v-row>
      </template>
    </v-select>

    <v-text-field
      v-model="mainLoopSleep"
      outlined
      :hint="
        !!fileConfig.sleepSeconds
          ? $t('backend_settings.config_file_disabled')
          : $t('backend_settings.main_loop_sleep.hint')
      "
      :label="$t('backend_settings.main_loop_sleep.label')"
      :disabled="!!fileConfig.sleepSeconds"
      :persistent-hint="!!fileConfig.sleepSeconds"
      type="number"
    />

    <v-checkbox
      v-model="logFromOtherModules"
      :label="$t('backend_settings.log_from_other_modules.label')"
      :disabled="!!fileConfig.logFromOtherModules"
      persistent-hint
      :hint="
        !!fileConfig.logFromOtherModules
          ? $t('backend_settings.config_file_disabled')
          : $t('backend_settings.log_from_other_modules.hint')
      "
    />

    <template #buttons>
      <v-spacer />
      <v-btn depressed>{{ $t('backend_settings.actions.cancel') }}</v-btn>
      <v-btn depressed color="primary">
        {{ $t('backend_settings.actions.save') }}
      </v-btn>
    </template>
  </card>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import BackendMixin from '@/mixins/backend-mixin';
import {
  CRITICAL,
  DEBUG,
  ERROR,
  INFO,
  Level,
  levels,
  WARN
} from '@/utils/log-level';

@Component({
  name: 'BackendSettings'
})
export default class BackendSettings extends Mixins(BackendMixin) {
  dataDirectory: string = '';
  logDirectory: string = '';
  logFromOtherModules: boolean = false;
  mainLoopSleep: string = '';

  readonly levels = levels;
  selecting: boolean = false;

  icon(level: Level): string {
    if (level === DEBUG) {
      return 'mdi-bug';
    } else if (level === INFO) {
      return 'mdi-information';
    } else if (level === WARN) {
      return 'mdi-alert';
    } else if (level === ERROR) {
      return 'mdi-alert-circle';
    } else if (level === CRITICAL) {
      return 'mdi-alert-decagram';
    }
    throw new Error(`Invalid option: ${level}`);
  }

  mounted() {
    this.dataDirectory = this.config.dataDirectory;
    this.logDirectory = this.config.logDirectory;
    this.loglevel = this.config.loglevel;
    this.mainLoopSleep = this.config.sleepSeconds ?? '';
    this.logFromOtherModules = this.config.logFromOtherModules ?? false;
  }

  save() {}

  async selectDirectory() {
    if (this.selecting) {
      return;
    }
    this.selecting = true;
    try {
      const directory = await this.$interop.openDirectory(
        this.$t('backend_settings.data_directory.select').toString()
      );
      if (directory) {
        this.dataDirectory = directory;
      }
    } finally {
      this.selecting = false;
    }
  }
}
</script>

<style scoped lang="scss"></style>
