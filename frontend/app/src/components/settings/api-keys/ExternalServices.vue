<template>
  <card>
    <template #title>
      {{ $t('external_services.title') }}
    </template>
    <template #subtitle>
      {{ $t('external_services.subtitle') }}
    </template>

    <api-key-box>
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
    </api-key-box>

    <api-key-box>
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
    </api-key-box>

    <api-key-box>
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
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="covalentKey"
        class="external-services__covalent-key"
        :title="$t('external_services.covalent.title')"
        :description="$t('external_services.covalent.description')"
        :label="$t('external_services.covalent.label')"
        :hint="$t('external_services.covalent.hint')"
        :loading="loading"
        :tooltip="$t('external_services.covalent.delete_tooltip')"
        @save="save('covalent', $event)"
        @delete-key="deleteKey('covalent')"
      />
    </api-key-box>

    <api-key-box>
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
    </api-key-box>

    <api-key-box>
      <service-key
        v-model="openseaKey"
        class="external-services__opensea-key"
        :title="$t('external_services.opensea.title')"
        :description="$t('external_services.opensea.description')"
        :label="$t('external_services.opensea.label')"
        :hint="$t('external_services.opensea.hint')"
        :loading="loading"
        :tooltip="$t('external_services.opensea.delete_tooltip')"
        @save="save('opensea', $event)"
        @delete-key="deleteKey('opensea')"
      >
        <i18n tag="div" path="external_services.opensea.link">
          <template #link>
            <external-link
              url="https://docs.opensea.io/reference/request-an-api-key"
            >
              {{ $t('external_services.opensea.here') }}
            </external-link>
          </template>
        </i18n>
      </service-key>
    </api-key-box>

    <confirm-dialog
      :title="$t('external_services.confirmation.title')"
      :message="$t('external_services.confirmation.message')"
      :display="!!serviceToDelete"
      @confirm="confirmDelete"
      @cancel="serviceToDelete = ''"
    />
  </card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ApiKeyBox from '@/components/settings/api-keys/ApiKeyBox.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import { Message } from '@/store/types';
import { Module } from '@/types/modules';
import {
  ExternalServiceKey,
  ExternalServiceKeys,
  ExternalServiceName
} from '@/types/user';

@Component({
  components: { ExternalLink, ApiKeyBox, ServiceKey, ConfirmDialog },
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
  covalentKey: string = '';
  beaconchainKey: string = '';
  loopringKey: string = '';
  openseaKey: string = '';

  serviceToDelete: ExternalServiceName | '' = '';

  loading: boolean = false;
  activeModules!: Module[];
  fetchLoopringBalances!: (refresh: boolean) => Promise<void>;

  get isLoopringActive(): boolean {
    return this.activeModules.includes(Module.LOOPRING);
  }

  private updateKeys({
    cryptocompare,
    covalent,
    etherscan,
    beaconchain,
    loopring,
    opensea
  }: ExternalServiceKeys) {
    this.cryptocompareKey = cryptocompare?.apiKey || '';
    this.covalentKey = covalent?.apiKey || '';
    this.etherscanKey = etherscan?.apiKey || '';
    this.beaconchainKey = beaconchain?.apiKey || '';
    this.loopringKey = loopring?.apiKey || '';
    this.openseaKey = opensea?.apiKey || '';
  }

  async mounted() {
    this.loading = true;
    this.updateKeys(await this.$api.queryExternalServices());
    this.loading = false;
  }

  async save(serviceName: ExternalServiceName, key: string) {
    const keys: ExternalServiceKey[] = [
      { name: serviceName, apiKey: key.trim() }
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
    } catch (e: any) {
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
    } catch (e: any) {
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
