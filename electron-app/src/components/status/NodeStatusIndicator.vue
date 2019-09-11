<template>
  <v-menu id="node-status-dropdown" transition="slide-y-transition" bottom>
    <template #activator="{ on }">
      <v-btn color="primary" dark icon text v-on="on">
        <v-icon> fa {{ nodeConnection ? 'fa-link' : 'fa-unlink' }} </v-icon>
      </v-btn>
    </template>
    <v-row class="node-status-indicator__content">
      <v-col cols="2">
        <v-icon v-if="nodeConnection" color="primary">
          fa fa-check-circle
        </v-icon>
        <v-icon v-else color="warning">fa fa-exclamation-triangle</v-icon>
      </v-col>
      <v-col cols="10">
        <span v-if="nodeConnection">
          Connected to a local ethereum node
        </span>
        <span v-else>
          Not connected to a local ethereum node
        </span>
      </v-col>
    </v-row>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';

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
