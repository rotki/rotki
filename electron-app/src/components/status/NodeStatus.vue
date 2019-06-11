<template>
  <li class="list-group-item eth-node-status">
    <a class="eth-node-status-link" href="#">
      <i
        class="fa fa-fw"
        :class="{ 'fa-link': nodeConnection, 'fa-unlink': !nodeConnection }"
      ></i>
    </a>
    <ul
      class="dropdown-menu dropdown-eth-status "
      :class="{ success: nodeConnection, warning: !nodeConnection }"
    >
      <li v-if="nodeConnection">Connected to a local ethereum node</li>
      <li v-else>Not connected to a local ethereum node</li>
    </ul>
  </li>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';

@Component({
  computed: mapState(['nodeConnection'])
})
export default class NodeStatus extends Vue {
  nodeConnection!: boolean;
}
</script>

<style scoped></style>
