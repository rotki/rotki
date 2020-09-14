<template>
  <div>
    <v-card class="manual-balances mt-8">
      <v-card-title>{{ $t('manual_balances.title') }}</v-card-title>
      <v-card-text>
        <v-btn
          absolute
          fab
          top
          right
          dark
          color="primary"
          class="manual-balances__add-balance"
          @click="newBalance()"
        >
          <v-icon>
            mdi-plus
          </v-icon>
        </v-btn>
        <big-dialog
          :display="openDialog"
          :title="dialogTitle"
          :subtitle="dialogSubtitle"
          :action-disabled="dialogDisabled || !valid"
          :loading="dialogLoading"
          primary-action="Save"
          @confirm="save()"
          @cancel="cancel()"
        >
          <manual-balances-form
            ref="dialogChild"
            v-model="valid"
            :edit="balanceToEdit"
          />
        </big-dialog>
        <manual-balances-list @editBalance="edit($event)" />
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ManualBalancesForm from '@/components/accounts/ManualBalancesForm.vue';
import ManualBalancesList from '@/components/accounts/ManualBalancesList.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { ManualBalance } from '@/services/balances/types';

@Component({
  components: {
    ManualBalancesList,
    ManualBalancesForm,
    BigDialog
  }
})
export default class ManualBalances extends Vue {
  balanceToEdit: ManualBalance | null = null;
  dialogTitle: string = '';
  dialogSubtitle: string = '';
  openDialog: boolean = false;
  dialogDisabled: boolean = false;
  dialogLoading: boolean = false;
  valid: boolean = false;

  newBalance() {
    this.dialogTitle = 'Add Manual Balance';
    this.dialogSubtitle = '';
    this.openDialog = true;
  }

  edit(balance: ManualBalance) {
    this.balanceToEdit = balance;
    this.dialogTitle = 'Edit Manual Balance';
    this.dialogSubtitle = 'Modify balance amount, location, and tags';
    this.openDialog = true;
  }

  async save() {
    this.dialogDisabled = true;
    this.dialogLoading = true;

    interface dataForm extends Vue {
      save(): Promise<boolean>;
    }
    const form = this.$refs.dialogChild as dataForm;
    const success = await form.save();
    this.dialogDisabled = false;
    this.dialogLoading = false;

    if (!success) {
      return;
    }
    this.openDialog = false;
    this.balanceToEdit = null;
  }

  cancel() {
    this.openDialog = false;
    this.balanceToEdit = null;
  }
}
</script>

<style scoped></style>
