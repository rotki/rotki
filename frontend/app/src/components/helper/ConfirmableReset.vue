<template>
  <v-menu v-model="menu" :nudge-width="150" offset-x>
    <template #activator="{ on: menu, attrs}">
      <v-tooltip top>
        <template #activator="{ on: tooltip }">
          <v-btn
            v-bind="attrs"
            text
            fab
            depressed
            :disabled="loading"
            v-on="{ ...menu, ...tooltip }"
          >
            <v-icon color="primary">mdi-database-refresh</v-icon>
          </v-btn>
        </template>
        <span>
          {{ tooltip }}
        </span>
      </v-tooltip>
    </template>
    <v-card max-width="280px">
      <v-card-title>{{ $t('confirmable_reset.confirm.title') }}</v-card-title>
      <v-card-text>
        <slot>{{ $t('confirmable_reset.confirm.message') }}</slot>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn text @click="menu = false">
          {{ $t('confirmable_reset.confirm.cancel') }}
        </v-btn>
        <v-btn color="primary" text @click="reset()">
          {{ $t('confirmable_reset.confirm.confirm') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-menu>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ConfirmableReset extends Vue {
  @Prop({ required: false })
  tooltip!: string;
  @Prop({ required: false })
  loading!: string;

  menu: boolean = false;

  @Emit()
  reset() {
    this.menu = false;
  }
}
</script>
