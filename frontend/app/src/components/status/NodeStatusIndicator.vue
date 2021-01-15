<template>
  <v-menu
    class="node-status-indicator"
    transition="slide-y-transition"
    offset-y
    bottom
    z-index="215"
  >
    <template #activator="{ on }">
      <menu-tooltip-button
        tooltip="Ethereum Node Status"
        class-name="secondary--text text--lighten-2"
        :on-menu="on"
      >
        <v-icon
          :class="`node-status-indicator__icon--${
            nodeConnection ? 'connected' : 'disconnected'
          }`"
          v-text="nodeConnection ? 'mdi-link' : 'mdi-link-off'"
        />
      </menu-tooltip-button>
    </template>
    <v-container>
      <v-row class="node-status-indicator__content">
        <v-col cols="2">
          <v-icon
            v-if="nodeConnection"
            color="primary"
            class="node-status-indicator__content__icon--connected"
          >
            mdi-check-circle
          </v-icon>
          <v-icon
            v-else
            color="warning"
            class="node-status-indicator__content__icon--disconnected"
          >
            mdi-alert
          </v-icon>
        </v-col>
        <v-col cols="10">
          <span
            v-if="nodeConnection"
            class="node-status-indicator__content__text--connected"
            v-text="$t('node_status_indicator.connected')"
          />
          <span
            v-else
            class="node-status-indicator__content__text--disconnected"
            v-text="$t('node_status_indicator.disconnected')"
          />
        </v-col>
      </v-row>
    </v-container>
  </v-menu>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

@Component({
  components: { MenuTooltipButton },
  computed: mapState('session', ['nodeConnection'])
})
export default class NodeStatusIndicator extends Vue {
  nodeConnection!: boolean;
}
</script>

<style scoped lang="scss">
.node-status-indicator {
  &__content {
    background: white;
    padding: 16px;
    width: 420px;
  }
}
</style>
