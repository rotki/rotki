<template>
  <card>
    <template #title>{{ $t('backend_settings.title') }}</template>
    <template #subtitle>{{ $t('backend_settings.subtitle') }}</template>

    <v-text-field
      v-model="dataDirectory"
      outlined
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
    <v-select
      v-model="loglevel"
      :items="levels"
      :label="$t('backend_settings.settings.log_level.label')"
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
  currentLogLevel,
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
    this.dataDirectory = this.getDataDirectory();
    this.loglevel = currentLogLevel();
  }

  save() {
    this.setLogLevel(this.loglevel);
    this.setDataDirectory(this.dataDirectory);
  }

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
