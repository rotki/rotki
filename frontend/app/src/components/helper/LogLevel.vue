<template>
  <v-menu class="log-level">
    <template #activator="{ on: menu, attrs}">
      <v-tooltip left max-width="280">
        <template #activator="{ on: tooltip }">
          <v-btn
            v-bind="attrs"
            text
            fab
            depressed
            v-on="{ ...menu, ...tooltip }"
          >
            <v-icon color="primary">mdi-cog</v-icon>
          </v-btn>
        </template>
        <span v-text="$t('loglevel.tooltip')" />
      </v-tooltip>
    </template>
    <v-list>
      <v-list-item-group
        :value="value"
        color="primary"
        mandatory
        @change="input($event)"
      >
        <v-list-item v-for="level in levels" :key="level" :value="level">
          <v-list-item-icon>
            <v-icon>{{ icon(level) }}</v-icon>
          </v-list-item-icon>
          <v-list-item-title>{{ level.toLocaleLowerCase() }}</v-list-item-title>
        </v-list-item>
      </v-list-item-group>
    </v-list>
  </v-menu>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import {
  CRITICAL,
  DEBUG,
  ERROR,
  INFO,
  Level,
  levels,
  WARN
} from '@/utils/log-level';

@Component({})
export default class LogLevel extends Vue {
  readonly levels = levels;
  @Prop({
    required: true,
    type: String,
    validator: value => levels.includes(value)
  })
  value!: Level;
  @Emit()
  input(_value: Level) {}

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
}
</script>

<style scoped lang="scss"></style>
