<template>
  <v-row justify="end">
    <v-col cols="auto">
      <v-sheet outlined :style="style">
        <v-row align="center" justify="center" no-gutters>
          <v-col
            v-for="module in moduleStatus"
            :key="module.identifier"
            cols="auto"
          >
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  x-small
                  v-bind="attrs"
                  icon
                  class="ma-2"
                  :class="module.enabled ? null : 'active-modules__disabled'"
                  v-on="on"
                  @click="onModulePress(module)"
                >
                  <v-img
                    width="24px"
                    height="24px"
                    contain
                    :src="icon(module.identifier)"
                  />
                </v-btn>
              </template>
              <span v-if="module.enabled">
                {{
                  $t('active_modules.view_addresses', {
                    name: name(module.identifier)
                  })
                }}
              </span>
              <span v-else>
                {{
                  $t('active_modules.activate', {
                    name: name(module.identifier)
                  })
                }}
              </span>
            </v-tooltip>
          </v-col>
        </v-row>
      </v-sheet>
      <queried-address-dialog
        :module="manageModule"
        @close="manageModule = null"
      />
      <confirm-dialog
        :title="$t('active_modules.enable.title')"
        :message="
          $t('active_modules.enable.description', { name: name(confirmEnable) })
        "
        :display="!!confirmEnable"
        @cancel="confirmEnable = null"
        @confirm="enableModule()"
      />
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import QueriedAddressDialog from '@/components/defi/QueriedAddressDialog.vue';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import { SupportedModules } from '@/services/session/types';
import { Nullable } from '@/types';
import { SettingsUpdate } from '@/typing/types';
import { assert } from '@/utils/assertions';

type ModuleWithStatus = {
  readonly identifier: SupportedModules;
  readonly enabled: boolean;
};

@Component({
  name: 'ActiveModules',
  components: { ConfirmDialog, QueriedAddressDialog, LabeledAddressDisplay },
  computed: {
    ...mapGetters('session', ['activeModules'])
  },
  methods: {
    ...mapActions('session', ['updateSettings', 'fetchQueriedAddresses'])
  }
})
export default class ActiveModules extends Vue {
  @Prop({ required: true, type: Array })
  modules!: SupportedModules[];

  fetchQueriedAddresses!: () => Promise<void>;
  updateSettings!: (update: SettingsUpdate) => Promise<void>;
  activeModules!: SupportedModules[];
  manageModule: Nullable<SupportedModules> = null;
  confirmEnable: Nullable<SupportedModules> = null;

  get style() {
    return {
      width: `${this.modules.length * 38}px`
    };
  }

  get moduleStatus(): ModuleWithStatus[] {
    return this.modules
      .map(module => ({
        identifier: module,
        enabled: this.activeModules.includes(module)
      }))
      .sort((a, b) => (a.enabled === b.enabled ? 0 : a.enabled ? -1 : 1));
  }

  name(module: string): string {
    const data = SUPPORTED_MODULES.find(value => value.identifier === module);
    return data?.name ?? '';
  }

  icon(module: SupportedModules): string {
    const data = SUPPORTED_MODULES.find(value => value.identifier === module);
    return data?.icon ?? '';
  }

  onModulePress(module: ModuleWithStatus) {
    if (module.enabled) {
      this.manageModule = module.identifier;
    } else {
      this.confirmEnable = module.identifier;
    }
  }

  enableModule() {
    assert(this.confirmEnable !== null);
    this.updateSettings({
      active_modules: [...this.activeModules, this.confirmEnable]
    });
    this.confirmEnable = null;
  }

  async mounted() {
    await this.fetchQueriedAddresses();
  }
}
</script>

<style scoped lang="scss">
.active-modules {
  &__disabled {
    filter: grayscale(100%);
  }
}
</style>
