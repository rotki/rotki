<template>
  <setting-category>
    <template #title>{{ $t('ledger_action_settings.title') }}</template>
    <template #subtitle>
      {{ $t('ledger_action_settings.subtitle') }}
    </template>
    <action-status-indicator :status="status" />
    <v-sheet outlined rounded>
      <v-simple-table>
        <thead>
          <tr>
            <th>{{ $t('ledger_action_settings.header.ledger_action') }}</th>
            <th>{{ $t('ledger_action_settings.header.taxable') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in ledgerActionData" :key="entry.identifier">
            <td>{{ entry.label }}</td>
            <td>
              <v-checkbox
                v-model="taxable[entry.identifier]"
                @change="changed(entry.identifier, $event)"
              />
            </td>
          </tr>
        </tbody>
      </v-simple-table>
    </v-sheet>
  </setting-category>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import SettingsMixin from '@/mixins/settings-mixin';
import { ledgerActionsData, LedgerActionType } from '@/store/history/consts';
import { ActionStatus } from '@/store/types';

const defaultTaxable: () => TaxableState = () => {
  const status: any = {};
  for (const action of Object.values(LedgerActionType)) {
    status[action] = false;
  }

  return status as TaxableState;
};

type TaxableState = { [key in LedgerActionType]: boolean };
@Component({
  components: { ActionStatusIndicator, SettingCategory }
})
export default class LedgerActionSettings extends Mixins(SettingsMixin) {
  readonly ledgerActionData = ledgerActionsData;
  taxable: TaxableState = defaultTaxable();
  status: ActionStatus | null = null;

  async changed() {
    const taxableActions: LedgerActionType[] = [];
    for (const actionType in this.taxable) {
      if (this.taxable[actionType as LedgerActionType]) {
        taxableActions.push(actionType as LedgerActionType);
      }
    }

    const status = await this.settingsUpdate({
      taxable_ledger_actions: taxableActions
    });

    if (!status.success) {
      this.status = status;
    }
  }

  mounted() {
    for (let taxableAction of this.accountingSettings.taxableLedgerActions) {
      this.taxable[taxableAction] = true;
    }
  }
}
</script>
