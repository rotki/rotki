<template>
  <v-tooltip top>
    <template #activator="{ on, attrs }">
      <v-btn
        fab
        text
        depressed
        :disabled="loading"
        v-bind="attrs"
        @click="refresh"
        v-on="on"
      >
        <v-icon color="primary">mdi-refresh</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class RefreshButton extends Vue {
  @Prop({ required: true, type: Boolean })
  loading!: boolean;
  @Prop({ required: true, type: String })
  tooltip!: string;
  @Emit()
  refresh() {}
}
</script>
