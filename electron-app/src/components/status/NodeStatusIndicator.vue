<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-menu id="node-status-dropdown" transition="slide-y-transition" bottom>
    <template v-slot:activator="{ on }">
      <v-btn color="primary" dark icon flat v-on="on">
        <v-icon>
          fa fa-fw {{ nodeConnection ? 'fa-link' : 'fa-unlink' }}
        </v-icon>
        <v-icon>fa fa-caret-down</v-icon>
      </v-btn>
    </template>
    <v-layout class="popup">
      <v-flex>
        <v-icon v-if="nodeConnection" color="primary">
          fa fa-fw fa-check-circle
        </v-icon>
        <v-icon v-else color="warning">fa fa-fw fa-exclamation-triangle</v-icon>
      </v-flex>
      <v-flex>
        <span v-if="nodeConnection">
          Connected to a local ethereum node
        </span>
        <span v-else>
          Not connected to a local ethereum node
        </span>
      </v-flex>
    </v-layout>
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
.popup {
  background: white;
  padding: 16px;
}
</style>
