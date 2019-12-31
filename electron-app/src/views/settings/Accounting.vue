<template>
  <v-container id="settings-account">
    <v-row>
      <v-col>
        <h1 class="page-header">Accounting Settings</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Trade Settings</v-card-title>
          <v-card-text>
            <v-switch
              id="crypto2crypto"
              v-model="crypto2CryptoTrades"
              label="Take into account crypto to crypto trades"
              color="primary"
              @change="onCrypto2CryptoChange($event)"
            ></v-switch>
            <v-switch
              id="include_gas_costs"
              v-model="gasCosts"
              label="Take into account Ethereum gas costs"
              color="primary"
              @change="onGasCostChange($event)"
            ></v-switch>
            <v-switch
              id="taxfree_period_exists"
              v-model="taxFreePeriod"
              label="Is there a tax free period?"
              color="primary"
              @change="onTaxFreeChange($event)"
            ></v-switch>
            <v-text-field
              v-model="taxFreeAfterPeriod"
              :disabled="!taxFreePeriod"
              label="Tax free after how many days"
              type="number"
            >
            </v-text-field>
          </v-card-text>
          <v-card-actions>
            <v-btn
              id="modify_trade_settings"
              depressed
              color="primary"
              type="submit"
              @click="modifyTradeSettings()"
            >
              Set
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Asset Settings</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="10">
                <v-text-field
                  v-model="assetToIgnore"
                  label="Asset To Ignore"
                  @keyup.enter="addAsset()"
                ></v-text-field>
              </v-col>
              <v-col cols="2">
                <v-btn
                  text
                  color="primary"
                  :disabled="assetToIgnore === ''"
                  @click="addAsset()"
                >
                  Add
                </v-btn>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="10">
                <v-select
                  v-model="assetToRemove"
                  :items="ignoredAssets"
                  hint="Click to see all ignored assets and select one for removal"
                  label="Ignored Assets"
                >
                  <div slot="append-outer">
                    <v-badge>
                      <template #badge>
                        <span>{{ ignoredAssets.length }}</span>
                      </template>
                    </v-badge>
                  </div>
                </v-select>
              </v-col>
              <v-col cols="2">
                <v-btn
                  text
                  color="primary"
                  :disabled="assetToRemove === ''"
                  @click="removeAsset()"
                >
                  Remove
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <div id="settings-accounting"></div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { AccountingSettings } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Message } from '@/store/store';

const { mapState } = createNamespacedHelpers('session');

@Component({
  components: {
    MessageDialog
  },
  computed: mapState(['accountingSettings'])
})
export default class Accounting extends Vue {
  accountingSettings!: AccountingSettings;

  crypto2CryptoTrades: boolean = false;
  gasCosts: boolean = false;
  taxFreeAfterPeriod: number | null = null;
  taxFreePeriod: boolean = false;

  ignoredAssets: string[] = [];
  assetToIgnore: string = '';
  assetToRemove: string = '';

  created() {
    this.$api
      .ignoredAssets()
      .then(assets => {
        this.ignoredAssets = assets;
      })
      .catch(() => {
        this.$store.commit('setMessage', {
          title: 'Error',
          description: 'Failed to retrieve the ignored assets'
        } as Message);
      });
  }

  mounted() {
    this.crypto2CryptoTrades = this.accountingSettings.includeCrypto2Crypto;
    this.gasCosts = this.accountingSettings.includeGasCosts;
    if (this.accountingSettings.taxFreeAfterPeriod) {
      this.taxFreePeriod = true;
      this.taxFreeAfterPeriod =
        this.accountingSettings.taxFreeAfterPeriod / 86400;
    } else {
      this.taxFreePeriod = false;
      this.taxFreeAfterPeriod = null;
    }
  }

  modifyTradeSettings() {
    let period = this.taxFreeAfterPeriod;
    if (period !== null) {
      period *= 86400;
    } else {
      period = -1;
    }

    const { commit } = this.$store;

    this.$api
      .setSettings({ taxfree_after_period: period })
      .then(() => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set trade settings',
          success: true
        } as Message);

        commit('session/accountingSettings', {
          ...this.accountingSettings,
          taxFreeAfterPeriod: period
        });
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Error setting trade settings',
          description: reason.message
        } as Message);
      });
  }

  onTaxFreeChange(enabled: boolean) {
    if (!enabled) {
      this.taxFreeAfterPeriod = null;
    } else {
      const period = this.accountingSettings.taxFreeAfterPeriod;
      if (period) {
        this.taxFreeAfterPeriod = period / 86400;
      } else {
        this.taxFreeAfterPeriod = 0;
      }
    }
  }

  onCrypto2CryptoChange(enabled: boolean) {
    const { commit } = this.$store;
    this.$api
      .setSettings({ include_crypto2crypto: enabled })
      .then(() => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set crypto to crypto consideration value',
          success: true
        } as Message);
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeCrypto2Crypto: enabled
        });
      })
      .catch(reason => {
        commit('setMessage', {
          title: 'Error',
          description: `Error setting crypto to crypto ${reason.message}`
        } as Message);
      });
  }

  onGasCostChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ include_gas_costs: enabled })
      .then(() => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set Ethereum gas costs value',
          success: true
        } as Message);
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeGasCosts: enabled
        });
      })
      .catch(reason => {
        commit('setMessage', {
          title: 'Error',
          description: `Error setting Ethereum gas costs: ${reason.message}`
        } as Message);
      });
  }

  addAsset() {
    const { commit } = this.$store;

    this.$api
      .modifyAsset(true, this.assetToIgnore)
      .then(() => {
        this.ignoredAssets.push(this.assetToIgnore);
        this.assetToIgnore = '';
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Ignored Asset Modification Error',
          description: `Error at modifying ignored asset ${this.assetToIgnore} (${reason.message})`
        } as Message);
      });
  }

  removeAsset() {
    this.$api
      .modifyAsset(false, this.assetToRemove)
      .then(() => {
        const index = this.ignoredAssets.findIndex(
          value => value == this.assetToRemove
        );
        if (index >= 0) {
          this.ignoredAssets.splice(index, 1);
        }
        this.assetToRemove = '';
      })
      .catch((reason: Error) => {
        const { commit } = this.$store;

        commit('setMessage', {
          title: 'Ignored Asset Modification Error',
          description: `Error at modifying ignored asset ${this.assetToIgnore} (${reason.message})`
        } as Message);
      });
  }
}
</script>

<style scoped></style>
