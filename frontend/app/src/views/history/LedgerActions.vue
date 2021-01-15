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
        @click="showForm()"
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
          show-expand
          single-expand
          item-key="identifier"
          :items="ledgerActions.data"
          :headers="headers"
          :footer-props="footerProps"
        >
          <template #item.actionType="{ item }">
            <event-type-display :event-type="item.actionType" />
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
          <template #item.actions="{ item }">
            <row-actions
              :disabled="refreshing"
              :edit-tooltip="$t('ledger_actions.edit_tooltip')"
              :delete-tooltip="$t('ledger_actions.delete_tooltip')"
              @edit-click="showForm(item)"
              @delete-click="deleteIdentifier = item.identifier"
            />
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
          <template #expanded-item="{ headers, item }">
            <td
              :colspan="headers.length"
              class="ledger-actions__action__details"
            >
              <v-col cols="12">
                <v-row class="pt-3 pb-3">
                  <span class="text-h6">
                    {{ $t('ledger_actions.details.title') }}
                  </span>
                </v-row>
                <v-row>
                  <v-col>
                    <v-card outlined>
                      <v-card-title class="subtitle-2">
                        {{ $t('ledger_actions.details.notes') }}
                      </v-card-title>
                      <v-card-text>
                        {{
                          item.notes
                            ? item.notes
                            : $t('ledger_actions.details.note_data')
                        }}
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
                <v-row class="mt-2">
                  <v-col cols="auto" class="font-weight-medium">
                    {{ $t('ledger_actions.details.link') }}
                  </v-col>
                  <v-col>
                    {{
                      item.link
                        ? item.link
                        : $t('ledger_actions.details.link_data')
                    }}
                  </v-col>
                </v-row>
              </v-col>
            </td>
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
      <ledger-action-form
        v-model="validForm"
        :action="action"
        :errors="errors"
        @action:update="action = $event"
      />
    </big-dialog>
    <confirm-dialog
      v-if="deleteIdentifier > 0"
      display
      :title="$t('ledger_actions.delete.title')"
      :message="$t('ledger_actions.delete.message')"
      @cancel="deleteIdentifier = 0"
      @confirm="deleteAction()"
    />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions, mapMutations, mapState } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import RowActions from '@/components/helper/RowActions.vue';
import LedgerActionForm from '@/components/history/LedgerActionForm.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { footerProps } from '@/config/datatable.common';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import StatusMixin from '@/mixins/status-mixin';
import { deserializeApiErrorMessage } from '@/services/converters';
import { Section } from '@/store/const';
import {
  ACTION_ADD_LEDGER_ACTION,
  ACTION_DELETE_LEDGER_ACTION,
  ACTION_EDIT_LEDGER_ACTION,
  ACTION_FETCH_LEDGER_ACTIONS,
  ACTION_INCOME
} from '@/store/history/consts';
import {
  HistoricData,
  LedgerAction,
  UnsavedAction
} from '@/store/history/types';
import { ActionStatus, Message } from '@/store/types';
import { Properties } from '@/types';
import { Zero } from '@/utils/bignumbers';

const emptyAction: () => UnsavedAction = () => ({
  timestamp: 0,
  actionType: ACTION_INCOME,
  location: TRADE_LOCATION_EXTERNAL,
  amount: Zero,
  asset: '',
  link: '',
  notes: ''
});

@Component({
  components: {
    ConfirmDialog,
    RowActions,
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
    ...mapActions('history', [
      ACTION_FETCH_LEDGER_ACTIONS,
      ACTION_ADD_LEDGER_ACTION,
      ACTION_EDIT_LEDGER_ACTION,
      ACTION_DELETE_LEDGER_ACTION
    ]),
    ...mapMutations(['setMessage'])
  }
})
export default class LedgerActions extends Mixins(StatusMixin) {
  readonly section = Section.LEDGER_ACTIONS;
  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('ledger_actions.headers.location').toString(),
      value: 'location'
    },
    {
      text: this.$t('ledger_actions.headers.type').toString(),
      value: 'actionType'
    },
    {
      text: this.$t('ledger_actions.headers.asset').toString(),
      value: 'asset'
    },
    {
      text: this.$t('ledger_actions.headers.amount').toString(),
      value: 'amount'
    },
    {
      text: this.$t('ledger_actions.headers.date').toString(),
      value: 'timestamp'
    },
    {
      text: this.$t('ledger_actions.headers.actions').toString(),
      align: 'end',
      value: 'actions'
    },
    { text: '', value: 'data-table-expand' }
  ];
  [ACTION_FETCH_LEDGER_ACTIONS]!: (refresh: boolean) => Promise<void>;
  [ACTION_ADD_LEDGER_ACTION]!: (action: UnsavedAction) => Promise<ActionStatus>;
  [ACTION_EDIT_LEDGER_ACTION]!: (action: LedgerAction) => Promise<ActionStatus>;
  [ACTION_DELETE_LEDGER_ACTION]!: (identifier: number) => Promise<ActionStatus>;
  setMessage!: (message: Message) => void;
  ledgerActions!: HistoricData<LedgerAction>;

  openDialog: boolean = false;
  validForm: boolean = false;
  deleteIdentifier: number = 0;
  action: LedgerAction | UnsavedAction = emptyAction();
  errors: { [key in Properties<UnsavedAction, any>]?: string } = {};

  async refresh() {
    await this[ACTION_FETCH_LEDGER_ACTIONS](true);
  }

  async mounted() {
    await this[ACTION_FETCH_LEDGER_ACTIONS](false);
  }

  async showForm(action: LedgerAction | UnsavedAction = emptyAction()) {
    this.action = action;
    this.openDialog = true;
  }

  async save() {
    let success: boolean;
    let message: string | undefined;
    if ('identifier' in this.action) {
      ({ success, message } = await this[ACTION_EDIT_LEDGER_ACTION](
        this.action
      ));
    } else {
      ({ success, message } = await this[ACTION_ADD_LEDGER_ACTION](
        this.action
      ));
    }

    if (success) {
      this.closeDialog();
    } else if (message) {
      const errors = deserializeApiErrorMessage(message) as any;
      if (errors) {
        this.errors = 'action' in errors ? errors['action'] : errors;
      } else {
        this.errors = {};
      }
    }
  }

  get dialogTitle(): string {
    return this.$t('ledger_actions.dialog.add.title').toString();
  }

  get dialogSubtitle(): string {
    return this.$t('ledger_actions.dialog.add.subtitle').toString();
  }

  async deleteAction() {
    const identifier = this.deleteIdentifier;
    this.deleteIdentifier = 0;
    const { success, message } = await this[ACTION_DELETE_LEDGER_ACTION](
      identifier
    );
    if (!success && message) {
      this.setMessage({
        success: false,
        description: this.$t('ledger_actions.delete_failure.description', {
          error: message
        }).toString(),
        title: this.$t('ledger_actions.delete_failure.title').toString()
      });
    }
  }

  closeDialog() {
    this.openDialog = false;
  }
}
</script>

<style scoped lang="scss">
.ledger-actions {
  &__action {
    &__details {
      background-color: var(--v-rotki-light-grey-base);
    }
  }
}
</style>
