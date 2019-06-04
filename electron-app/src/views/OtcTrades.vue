<template>
  <v-container>
    <otc-form
      :edit-mode="editMode"
      :otc-trade="editableItem"
      @save="saveItem($event)"
      @cancel="cancelEdit()"
    ></otc-form>
    <v-layout>
      <v-flex>
        <h1>OTC Trades List</h1>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex xs12>
        <v-card>
          <v-data-table
            :headers="headers"
            :items="otcTrades"
            :expand="expand"
            item-key="timestamp"
          >
            <template v-slot:items="props">
              <tr
                @click="props.expanded = !props.expanded"
                @contextmenu="show($event, props.item)"
              >
                <td class="text-xs-right">{{ props.item.pair }}</td>
                <td class="text-xs-right">{{ props.item.type }}</td>
                <td class="text-xs-right">{{ props.item.amount }}</td>
                <td class="text-xs-right">{{ props.item.rate }}</td>
                <td class="text-xs-right">
                  {{ props.item.timestamp | formatDate(dateDisplayFormat) }}
                </td>
              </tr>
            </template>
            <template v-slot:expand="props">
              <v-card flat>
                <v-card-title class="font-weight-bold">Details</v-card-title>
                <v-card-text>
                  <p v-if="props.item.notes">
                    <span class="font-weight-medium">Extra Info:</span>
                    {{ props.item.notes }}
                  </p>
                  <p v-if="props.item.link">
                    <span class="font-weight-medium">Links:</span>
                    {{ props.item.link }}}
                  </p>
                  <p v-if="props.item.fee">
                    <span class="font-weight-medium">Fee:</span>
                    {{ props.item.fee }} {{ props.item.fee_currency }}
                  </p>
                </v-card-text>
              </v-card>
            </template>
          </v-data-table>
          <v-menu
            v-model="showMenu"
            :position-x="x"
            :position-y="y"
            absolute
            offset-y
          >
            <v-list>
              <v-list-tile @click="editItem()">
                <v-list-tile-title>
                  Edit
                </v-list-tile-title>
              </v-list-tile>
              <v-list-tile @click="deleteItem()">
                <v-list-tile-title>
                  Delete
                </v-list-tile-title>
              </v-list-tile>
            </v-list>
          </v-menu>
        </v-card>
      </v-flex>
    </v-layout>
    <message-dialog
      title="Success"
      success
      :message="successMessage"
      @dismiss="successMessage = ''"
    ></message-dialog>
    <message-dialog
      title="Error"
      :message="errorMessage"
      @dismiss="errorMessage = ''"
    ></message-dialog>
    <div id="otc-trades"></div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import {
  add_otctrades_listeners,
  create_otctrades_ui
} from '@/legacy/otctrades';
import { create_or_reload_page } from '@/legacy/navigation';
import { OtcTrade } from '@/model/otc-trade';
import OtcForm from '@/components/OtcForm.vue';
import { mapGetters } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';

@Component({
  components: { MessageDialog, OtcForm },
  computed: mapGetters(['dateDisplayFormat'])
})
export default class OtcTrades extends Vue {
  dateDisplayFormat!: string;
  expand: boolean = false;
  showMenu: boolean = false;
  editMode: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';
  x: number = 0;
  y: number = 0;

  selectedItem?: OtcTrade;
  editableItem?: OtcTrade;

  otcTrades: OtcTrade[] = [];

  readonly headers = [
    { text: 'Pair', value: 'pair' },
    { text: 'Type', value: 'type' },
    { text: 'Amount', value: 'amount' },
    { text: 'Rate', value: 'rate' },
    { text: 'Time', value: 'timestamp' }
  ];

  show(event: any, item: OtcTrade) {
    event.preventDefault();
    this.showMenu = false;
    this.x = event.clientX;
    this.y = event.clientY;
    this.$nextTick(() => {
      this.showMenu = true;
    });
    this.selectedItem = item;
  }

  saveItem(otcTrade: OtcTrade) {
    this.$rpc
      .modify_otc_trades(this.editMode, otcTrade)
      .then(() => {
        this.successMessage = 'Trade submitted';
        this.fetchData();
      })
      .catch((reason: Error) => {
        this.errorMessage = `Trade Addition Error: ${reason.message}`;
      })
      .finally(() => {
        this.editMode = false;
        this.selectedItem = undefined;
        this.editableItem = undefined;
      });
  }

  editItem() {
    this.editMode = true;
    this.editableItem = this.selectedItem;
  }

  deleteItem() {
    this.$rpc
      .delete_otctrade(this.selectedItem!.id)
      .then(() => {
        this.successMessage = 'Trade Deleted';
        const index = this.otcTrades.indexOf(this.selectedItem!!);
        this.otcTrades.splice(index, 1);
      })
      .catch(reason => {
        this.errorMessage = `Error at Trade Deletion: ${reason.message}`;
      })
      .finally(() => {
        this.selectedItem = undefined;
      });
  }

  cancelEdit() {
    this.editMode = false;
    this.selectedItem = undefined;
    this.editableItem = undefined;
  }

  created() {
    this.fetchData();
  }

  private fetchData() {
    this.$rpc
      .query_otctrades()
      .then(value => {
        this.otcTrades = value;
      })
      .catch(reason => {
        this.errorMessage = `Trade loading failed: ${reason.message}`;
      });
  }

  mounted() {
    create_or_reload_page(
      'otctrades',
      create_otctrades_ui,
      add_otctrades_listeners,
      'otc-trades'
    );
  }
}
</script>

<style scoped></style>
