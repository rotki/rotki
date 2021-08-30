<template>
  <v-row
    :class="$style.content"
    :style="backgroundStyle"
    data-cy="status-content"
  >
    <v-col cols="auto">
      <v-icon v-if="connected" color="primary" data-cy="status-icon">
        mdi-check-circle
      </v-icon>
      <v-icon v-else color="warning" data-cy="status-icon"> mdi-alert </v-icon>
    </v-col>
    <v-col cols="10">
      <span v-if="connected" data-cy="status-text">
        {{ $t('node_status_indicator.connected') }}
      </span>
      <span v-else data-cy="status-text">
        {{ $t('node_status_indicator.disconnected') }}
      </span>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ThemeMixin from '@/mixins/theme-mixin';

export default defineComponent({
  name: 'NodeStatus',
  mixins: [ThemeMixin],
  props: {
    connected: {
      required: true,
      type: Boolean
    }
  }
});
</script>

<style module lang="scss">
.content {
  padding: 16px;
  width: 420px;
}
</style>
