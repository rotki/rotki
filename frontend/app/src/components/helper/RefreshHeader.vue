<template>
  <h2 class="d-flex justify-space-between align-center">
    {{ title }}

    <span>
      <v-tooltip top>
        <template #activator="{ on, attrs }">
          <v-btn
            text
            fab
            depressed
            :disabled="loading"
            v-bind="attrs"
            @click="refresh()"
            v-on="on"
          >
            <v-icon color="primary">fa-refresh</v-icon>
          </v-btn>
        </template>
        <span>Refreshes the {{ title.toLocaleLowerCase() }} data</span>
      </v-tooltip>
      <slot></slot>
    </span>
  </h2>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class RefreshHeader extends Vue {
  @Prop({ required: true, type: String })
  title!: string;

  @Prop({ required: true, type: Boolean })
  loading!: boolean;

  @Emit()
  refresh() {}
}
</script>

<style scoped></style>
