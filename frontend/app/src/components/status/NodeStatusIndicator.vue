<template>
  <v-menu
    data-cy="status-indicator"
    transition="slide-y-transition"
    offset-y
    z-index="215"
  >
    <template #activator="{ on }">
      <menu-tooltip-button
        tooltip="Ethereum Node Status"
        class-name="secondary--text text--lighten-2"
        :on-menu="on"
      >
        <v-icon v-if="nodeConnection">mdi-link</v-icon>
        <v-icon v-else>mdi-link-off</v-icon>
      </menu-tooltip-button>
    </template>
    <node-status :connected="nodeConnection" />
  </v-menu>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { mapState } from 'vuex';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import NodeStatus from '@/components/status/NodeStatus.vue';
import ThemeMixin from '@/mixins/theme-mixin';

export default defineComponent({
  name: 'NodeStatusIndicator',
  components: { NodeStatus, MenuTooltipButton },
  mixins: [ThemeMixin],
  computed: mapState('session', ['nodeConnection'])
});
</script>
