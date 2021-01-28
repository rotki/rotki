<template>
  <div class="action-status-indicator">
    <v-alert
      v-if="status"
      dense
      :color="status.success ? 'success' : 'error'"
      text
      outlined
      :icon="status.success ? 'mdi-check' : 'mdi-alert-circle-outline'"
    >
      {{ status.message }}
    </v-alert>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { ActionStatus } from '@/store/types';

@Component({})
export default class ActionStatusIndicator extends Vue {
  @Prop({ required: true })
  status!: ActionStatus | null;
}
</script>

<style scoped lang="scss">
.action-status-indicator {
  height: 48px;
  padding: 16px;
  margin-bottom: 8px;
}
</style>
