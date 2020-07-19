<template>
  <h2 class="d-flex justify-space-between align-center">
    {{ title }}

    <v-btn text fab depressed :disabled="loading" @click="refresh()">
      <v-icon color="primary">fa-refresh</v-icon>
    </v-btn>
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
