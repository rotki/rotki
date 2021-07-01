<template>
  <v-container>
    <v-card>
      <v-card-title>
        <card-title>{{ $t('external_services.title') }}</card-title>
      </v-card-title>
      <v-card-subtitle v-text="$t('external_services.subtitle')" />
      <v-card-text>
        <v-row no-gutters class="mt-4">
          <v-col cols="12">
            <v-sheet outlined rounded>
              <service-key
                v-model="etherscanKey"
                class="external-services__etherscan-key"
                :title="$t('external_services.etherscan.title')"
                :description="$t('external_services.etherscan.description')"
                :label="$t('external_services.etherscan.label')"
                :hint="$t('external_services.etherscan.hint')"
                :loading="loading"
                :tooltip="$t('external_services.etherscan.delete_tooltip')"
                @save="save('etherscan', $event)"
                @delete-key="deleteKey('etherscan')"
              />
            </v-sheet>
          </v-col>
        </v-row>
        <v-row no-gutters class="mt-8">
          <v-col cols="12">
            <v-sheet outlined rounded>
              <service-key
                v-model="cryptocompareKey"
                class="external-services__cryptocompare-key"
                :title="$t('external_services.cryptocompare.title')"
                :description="$t('external_services.cryptocompare.description')"
                :label="$t('external_services.cryptocompare.label')"
                :hint="$t('external_services.cryptocompare.hint')"
                :loading="loading"
                :tooltip="$t('external_services.cryptocompare.delete_tooltip')"
                @save="save('cryptocompare', $event)"
                @delete-key="deleteKey('cryptocompare')"
              />
            </v-sheet>
          </v-col>
        </v-row>
        <v-row no-gutters class="mt-8">
          <v-col cols="12">
            <v-sheet outlined rounded>
              <service-key
                v-model="beaconchainKey"
                class="external-services__beaconchain-key"
                :title="$t('external_services.beaconchain.title')"
                :description="$t('external_services.beaconchain.description')"
                :label="$t('external_services.beaconchain.label')"
                :hint="$t('external_services.beaconchain.hint')"
                :loading="loading"
                :tooltip="$t('external_services.beaconchain.delete_tooltip')"
                @save="save('beaconchain', $event)"
                @delete-key="deleteKey('beaconchain')"
              />
            </v-sheet>
          </v-col>
        </v-row>
        <v-row no-gutters class="mt-8">
          <v-col cols="12">
            <v-sheet outlined rounded>
              <service-key
                v-model="loopringKey"
                class="external-services__loopring_key"
                :title="$t('external_services.loopring.title')"
                :description="$t('external_services.loopring.description')"
                :label="$t('external_services.loopring.label')"
                :hint="$t('external_services.loopring.hint')"
                :loading="loading"
                :tooltip="$t('external_services.loopring.delete_tooltip')"
                @save="save('loopring', $event)"
                @delete-key="deleteKey('loopring')"
              />

              <v-alert
                v-if="loopringKey && !isLoopringActive"
                prominent
                type="warning"
                class="ma-2"
                outlined
              >
                <v-row align="center">
                  <v-col class="grow">
                    {{ $t('external_services.loopring.not_enabled') }}
                  </v-col>
                  <v-col class="shrink">
                    <v-btn to="/settings/modules" color="primary">
                      {{ $t('external_services.loopring.settings') }}
                    </v-btn>
                  </v-col>
                </v-row>
              </v-alert>
            </v-sheet>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <confirm-dialog
      :title="$t('external_services.confirmation.title')"
      :message="$t('external_services.confirmation.message')"
      :display="!!serviceToDelete"
      @confirm="confirmDelete"
      @cancel="serviceToDelete = ''"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { ExternalServiceKeys } from '@/model/action-result';
import { MODULE_LOOPRING } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
import { Message } from '@/store/types';
import { ExternalServiceKey, ExternalServiceName } from '@/typing/types';

@Component({
  components: { ServiceKey, ConfirmDialog },
  computed: {
    ...mapGetters('session', ['activeModules'])
  },
  methods: {
    ...mapActions('balances', ['fetchLoopringBalances'])
  }
})
export default class ExternalServices extends Vue {
  etherscanKey: string = '';
  cryptocompareKey: string = '';
  beaconchainKey: string = '';
  loopringKey: string = '';

  serviceToDelete: ExternalServiceName | '' = '';

  loading: boolean = false;
  activeModules!: SupportedModules[];
  fetchLoopringBalances!: (refresh: boolean) => Promise<void>;

  get isLoopringActive(): boolean {
    return this.activeModules.includes(MODULE_LOOPRING);
  }

  private updateKeys({
    cryptocompare,
    etherscan,
    beaconchain,
    loopring
  }: ExternalServiceKeys) {
    this.cryptocompareKey = cryptocompare?.api_key || '';
    this.etherscanKey = etherscan?.api_key || '';
    this.beaconchainKey = beaconchain?.api_key || '';
    this.loopringKey = loopring?.api_key || '';
  }

  async mounted() {
    this.loading = true;
    this.updateKeys(await this.$api.queryExternalServices());
    this.loading = false;
  }

  async save(serviceName: ExternalServiceName, key: string) {
    const keys: ExternalServiceKey[] = [
      { name: serviceName, api_key: key.trim() }
    ];

    try {
      this.loading = true;
      this.updateKeys(await this.$api.setExternalServices(keys));
      this.$store.commit('setMessage', {
        title: this.$t('external_services.set.success.title').toString(),
        description: this.$t('external_services.set.success.message', {
          serviceName
        }).toString(),
        success: true
      } as Message);
      if (serviceName === 'loopring') {
        await this.fetchLoopringBalances(true);
      }
    } catch (e) {
      this.$store.commit('setMessage', {
        title: this.$t('external_services.set.error.title').toString(),
        description: this.$t('external_services.set.error.message', {
          error: e.message
        }).toString()
      } as Message);
    }
    this.loading = false;
  }

  deleteKey(serviceName: ExternalServiceName) {
    this.serviceToDelete = serviceName;
  }

  async confirmDelete() {
    /* istanbul ignore if */
    if (!this.serviceToDelete) {
      return;
    }
    try {
      this.loading = true;
      this.updateKeys(
        await this.$api.deleteExternalServices(this.serviceToDelete)
      );
    } catch (e) {
      this.$store.commit('setMessage', {
        title: this.$t('external_services.delete_error.title').toString(),
        description: this.$t('external_services.delete_error.description', {
          message: e.message
        }).toString()
      } as Message);
    }
    this.loading = false;
    this.serviceToDelete = '';
  }
}
</script>
