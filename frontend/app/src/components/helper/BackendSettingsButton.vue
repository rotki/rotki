<template>
  <v-bottom-sheet v-model="visible" width="98%" class="backend-settings-button">
    <template #activator="{ on: menu, attrs }">
      <v-tooltip left max-width="280">
        <template #activator="{ on: tooltip }">
          <v-btn
            v-bind="attrs"
            text
            fab
            depressed
            v-on="{ ...menu, ...tooltip }"
          >
            <v-icon color="primary">mdi-cog</v-icon>
          </v-btn>
        </template>
        <span>{{ $t('backend_settings_button.tooltip') }}</span>
      </v-tooltip>
    </template>
    <backend-settings v-if="visible" @dismiss="visible = false" />
  </v-bottom-sheet>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import BackendSettings from '@/components/settings/BackendSettings.vue';

@Component({
  components: { BackendSettings }
})
export default class BackendSettingsButton extends Vue {
  visible: boolean = false;
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

::v-deep {
  .v-card {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
  }
}

.backend-settings-button {
  height: calc(100vh - 80px);
}
</style>
