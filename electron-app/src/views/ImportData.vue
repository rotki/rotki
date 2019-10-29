<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-row>
          <v-col cols="12">
            <h1 class="page-header">Import Data</h1>
          </v-col>
        </v-row>
        <v-row>
          <p>
            You can manually import data from the services below by clicking on
            the respective logo
          </p>
        </v-row>
        <v-row>
          <h3>Cointracking.info</h3>
        </v-row>
        <v-row>
          <p>
            Important notes for importing data from cointracking's CSV exports.
          </p>
          <ul>
            <li>
              Trades/deposits/withdrawals from Cointracking do not include fees.
            </li>
            <li>
              All timestamps are rounded up to the minute. That is extremely
              innacurate for fast paced trading.
            </li>
            <li>
              All trades imported from Cointracking will always be considered as
              buys due to the way the data are represented.
            </li>
            <li>
              ETH/BTC Transactions are treated as deposits/withdrawals so they
              are not imported in Rotkehlchen. To import ETH transactions simply
              input your accounts in user settings and they will be imported
              automatically for you.
            </li>
          </ul>
        </v-row>
        <v-row>
          <p>
            For the above reasons it's preferred to directly connect your
            exchanges in order to import data from there. If you do not do that
            a lot of accuracy is lost.
          </p>
        </v-row>
        <v-row>
          <v-col cols="3">
            <v-img
              class="import-data__cointracking-info elevation-1"
              :src="require('../assets/images/cointracking_info.png')"
              @click="coinTrackingInfoImport()"
            ></v-img>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { remote } from 'electron';
import { Message } from '@/store/store';

@Component({})
export default class ImportData extends Vue {
  async coinTrackingInfoImport() {
    remote.dialog.showOpenDialog(
      {
        title: 'Select a file',
        properties: ['openFile']
      },
      async filePaths => {
        if (!filePaths) {
          return;
        }

        const file = filePaths[0];
        this.$rpc
          .import_data_from('cointracking_info', file)
          .then(() => {
            this.$store.commit('setMessage', {
              success: true,
              title: 'Import successful',
              description:
                'Data imported from cointracking.info export file succesfuly'
            } as Message);
          })
          .catch((reason: Error) => {
            this.$store.commit('setMessage', {
              title: 'Import failed',
              description: reason.message
            } as Message);
          });
      }
    );
  }
}
</script>

<style scoped></style>
