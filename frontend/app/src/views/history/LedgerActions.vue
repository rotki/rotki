<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('ledger_actions.loading') }}
    </template>
    {{ $t('ledger_actions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <ledger-actions-content
      :items="ledgerActions"
      :total="ledgerActionsTotal"
      :limit="ledgerActionsLimit"
      :refreshing="refreshing"
      :loading="loading"
      @refresh="refresh"
      @show-form="showForm"
      @delete-action="setDeleteIdentifier"
    />
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :action-disabled="!validForm || saving"
      :primary-action="$t('ledger_actions.dialog.save')"
      @confirm="save()"
      @cancel="closeDialog()"
    >
      <ledger-action-form
        v-model="validForm"
        :action="action"
        :errors="errors"
        @action:update="updateAction($event)"
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
  </div>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters, mapMutations } from 'vuex';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import NotesDisplay from '@/components/helper/table/NotesDisplay.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LedgerActionForm from '@/components/history/LedgerActionForm.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import StatusMixin from '@/mixins/status-mixin';
import { deserializeApiErrorMessage } from '@/services/converters';
import { TradeLocation } from '@/services/history/types';
import { Section } from '@/store/const';
import {
  FETCH_FROM_SOURCE,
  FETCH_REFRESH,
  HistoryActions
} from '@/store/history/consts';
import {
  FetchSource,
  HistoricData,
  IgnoreActionPayload,
  LedgerAction,
  LedgerActionEntry,
  UnsavedAction
} from '@/store/history/types';
import { ActionStatus, Message } from '@/store/types';
import { Writeable } from '@/types';
import { LedgerActionType } from '@/types/ledger-actions';
import { Zero } from '@/utils/bignumbers';
import LedgerActionsContent from '@/views/history/LedgerActionsContent.vue';

const emptyAction: () => UnsavedAction = () => ({
  timestamp: 0,
  actionType: LedgerActionType.ACTION_INCOME,
  location: lastSelectedLocation(),
  amount: Zero,
  asset: ''
});

const LAST_LOCATION = 'rotki.ledger_action.location';

function setLastSelectedLocation(location: TradeLocation) {
  localStorage.setItem(LAST_LOCATION, location);
}

function lastSelectedLocation(): TradeLocation {
  const item = localStorage.getItem(LAST_LOCATION);
  if (item) {
    return item as TradeLocation;
  }
  return TRADE_LOCATION_EXTERNAL;
}

@Component({
  components: {
    LedgerActionsContent,
    NotesDisplay,
    IgnoreButtons,
    ConfirmDialog,
    LedgerActionForm,
    BigDialog,
    ProgressScreen
  },
  computed: {
    ...mapGetters('history', [
      'ledgerActions',
      'ledgerActionsTotal',
      'ledgerActionsLimit'
    ])
  },
  methods: {
    ...mapActions('history', [
      HistoryActions.FETCH_LEDGER_ACTIONS,
      HistoryActions.ADD_LEDGER_ACTION,
      HistoryActions.EDIT_LEDGER_ACTION,
      HistoryActions.DELETE_LEDGER_ACTION,
      HistoryActions.IGNORE_ACTIONS,
      HistoryActions.UNIGNORE_ACTION
    ]),
    ...mapMutations(['setMessage'])
  }
})
export default class LedgerActions extends Mixins(StatusMixin) {
  readonly section = Section.LEDGER_ACTIONS;
  [HistoryActions.FETCH_LEDGER_ACTIONS]!: (
    payload: FetchSource
  ) => Promise<void>;
  [HistoryActions.ADD_LEDGER_ACTION]!: (
    action: UnsavedAction
  ) => Promise<ActionStatus>;
  [HistoryActions.EDIT_LEDGER_ACTION]!: (
    action: LedgerAction
  ) => Promise<ActionStatus>;
  [HistoryActions.DELETE_LEDGER_ACTION]!: (
    identifier: number
  ) => Promise<ActionStatus>;
  ignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  unignoreActions!: (actionsIds: IgnoreActionPayload) => Promise<ActionStatus>;
  setMessage!: (message: Message) => void;
  ledgerActions!: HistoricData<LedgerActionEntry>;

  openDialog: boolean = false;
  validForm: boolean = false;
  saving: boolean = false;
  deleteIdentifier: number = 0;
  action: LedgerActionEntry | UnsavedAction = emptyAction();
  errors: { [key in keyof UnsavedAction]?: string } = {};

  updateAction(action: LedgerAction | UnsavedAction) {
    this.action = action;
    setLastSelectedLocation(action.location);
  }

  async refresh() {
    await this.fetch(FETCH_REFRESH);
  }

  async mounted() {
    await this.fetch(FETCH_FROM_SOURCE);
  }

  async fetch(source: FetchSource) {
    await this[HistoryActions.FETCH_LEDGER_ACTIONS](source);
  }

  async showForm(action: LedgerActionEntry | UnsavedAction = emptyAction()) {
    this.action = action;
    this.openDialog = true;
  }

  async save() {
    this.saving = true;
    const action: Writeable<LedgerActionEntry | UnsavedAction> = this.action;
    let success: boolean;
    let message: string | undefined;

    let prop: keyof typeof action;
    for (prop in action) {
      if (!action[prop]) {
        delete action[prop];
      }
    }

    if ('identifier' in action) {
      const { ignoredInAccounting, ...payload } = action as LedgerActionEntry;
      ({ success, message } = await this[HistoryActions.EDIT_LEDGER_ACTION](
        payload
      ));
    } else {
      const payload = { ...action };
      ({ success, message } = await this[HistoryActions.ADD_LEDGER_ACTION](
        payload
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
    this.saving = false;
  }

  get dialogTitle(): string {
    return this.$t('ledger_actions.dialog.add.title').toString();
  }

  get dialogSubtitle(): string {
    return this.$t('ledger_actions.dialog.add.subtitle').toString();
  }

  async setDeleteIdentifier(identifier: number) {
    this.deleteIdentifier = identifier;
  }

  async deleteAction() {
    const identifier = this.deleteIdentifier;
    this.deleteIdentifier = 0;
    const { success, message } = await this[
      HistoryActions.DELETE_LEDGER_ACTION
    ](identifier);
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

::v-deep {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
