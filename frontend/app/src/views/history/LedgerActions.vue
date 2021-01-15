<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('ledger_actions.loading') }}
    </template>
    {{ $t('ledger_actions.loading_subtitle') }}
  </progress-screen>
  <v-container v-else>
    <v-card>
      <v-btn
        absolute
        fab
        top
        right
        dark
        color="primary"
        class="ledger-actions__add"
        @click="addLedgerAction"
      >
        <v-icon> mdi-plus </v-icon>
      </v-btn>
      <v-card-title>
        <refresh-button
          :loading="refreshing"
          :tooltip="$t('ledger_actions.refresh_tooltip')"
          @refresh="refresh"
        />
        {{ $t('ledger_actions.title') }}
        <v-spacer />
      </v-card-title>
      <v-card-text>
        <v-data-table
          :items="ledgerActions.data"
          :headers="headers"
          :footer-props="footerProps"
        >
          <template #item.type="{ item }">
            <event-type-display :event-type="item.type" />
          </template>
          <template #item.timestamp="{ item }">
            <date-display :timestamp="item.timestamp" />
          </template>
          <template #item.location="{ item }">
            <location-display :identifier="item.location" />
          </template>
          <template #item.asset="{ item }">
            <asset-details :asset="item.asset" />
          </template>
          <template #item.amount="{ item }">
            <amount-display :value="item.amount" />
          </template>
          <template
            v-if="
              ledgerActions.limit <= ledgerActions.found &&
              ledgerActions.limit > 0
            "
            #body.append="{ headers }"
          >
            <upgrade-row
              :limit="ledgerActions.limit"
              :total="ledgerActions.found"
              :colspan="headers.length"
              :label="$t('ledger_actions.label')"
            />
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :action-disabled="!validForm"
      :primary-action="$t('ledger_actions.dialog.save')"
      @confirm="save()"
      @cancel="closeDialog()"
    >
      <ledger-action-form v-model="validForm" />
    </big-dialog>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapState } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import LedgerActionForm from '@/components/history/LedgerActionForm.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { footerProps } from '@/config/datatable.common';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';
import { ACTION_FETCH_LEDGER_ACTIONS } from '@/store/history/consts';
import { HistoricData, LedgerAction } from '@/store/history/types';

@Component({
  components: {
    LedgerActionForm,
    BigDialog,
    UpgradeRow,
    RefreshButton,
    ProgressScreen
  },
  computed: {
    ...mapState('history', ['ledgerActions'])
  },
  methods: {
    ...mapActions('history', [ACTION_FETCH_LEDGER_ACTIONS])
  }
})
export default class LedgerActions extends Mixins(StatusMixin) {
  readonly section = Section.LEDGER_ACTIONS;
  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    {
      text: 'Location',
      value: 'location'
    },
    {
      text: 'Type',
      value: 'type'
    },
    {
      text: 'Asset',
      value: 'asset'
    },
    {
      text: 'Amount',
      value: 'amount'
    },
    {
      text: 'Date',
      value: 'timestamp'
    },
    { text: '', value: 'data-table-expand' }
  ];
  [ACTION_FETCH_LEDGER_ACTIONS]!: (refresh: boolean) => Promise<void>;
  ledgerActions!: HistoricData<LedgerAction>;

  openDialog: boolean = false;
  validForm: boolean = false;

  async refresh() {
    await this[ACTION_FETCH_LEDGER_ACTIONS](true);
  }

  async mounted() {
    await this[ACTION_FETCH_LEDGER_ACTIONS](false);
  }

  async addLedgerAction() {
    this.openDialog = true;
  }

  get dialogTitle(): string {
    return this.$t('ledger_actions.dialog.add.title').toString();
  }

  get dialogSubtitle(): string {
    return this.$t('ledger_actions.dialog.add.subtitle').toString();
  }

  closeDialog() {
    this.openDialog = false;
  }
}
</script>

<style scoped lang="scss"></style>
