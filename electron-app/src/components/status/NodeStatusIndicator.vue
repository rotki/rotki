<template>
  <v-menu class="node-status-indicator" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon
          :class="
            `node-status-indicator__icon--${
              nodeConnection ? 'connected' : 'disconnected'
            }`
          "
        >
          fa {{ nodeConnection ? 'fa-link' : 'fa-unlink' }}
        </v-icon>
      </v-btn>
    </template>
    <v-row class="node-status-indicator__content">
      <v-col cols="2">
        <v-icon
          v-if="nodeConnection"
          color="primary"
          class="node-status-indicator__content__icon--connected"
        >
          fa fa-check-circle
        </v-icon>
        <v-icon
          v-else
          color="warning"
          class="node-status-indicator__content__icon--disconnected"
        >
          fa fa-exclamation-triangle
        </v-icon>
      </v-col>
      <v-col cols="10">
        <span
          v-if="nodeConnection"
          class="node-status-indicator__content__text--connected"
        >
          Connected to an ethereum node
        </span>
        <span v-else class="node-status-indicator__content__text--disconnected">
          Not connected to an ethereum node
        </span>
      </v-col>
    </v-row>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
const { mapState } = createNamespacedHelpers('session');

@Component({
  computed: mapState(['nodeConnection'])
})
export default class NodeStatusIndicator extends Vue {
  nodeConnection!: boolean;
}
</script>

<style scoped lang="scss">
.node-status-indicator__content {
  background: white;
  padding: 16px;
  width: 420px;
}
</style>
