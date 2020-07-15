<template>
  <v-card class="manual-balances mt-8">
    <v-card-title>Manually Tracked Balances</v-card-title>
    <v-card-text>
      <v-btn absolute fab top right dark color="primary" @click="newBalance()">
        <v-icon>
          fa fa-plus
        </v-icon>
      </v-btn>
      <big-dialog
        :display="openDialog"
        :title="dialogTitle"
        :sub-title="dialogSubTitle"
        primary-action="Save"
        @confirm="save()"
        @cancel="openDialog = false"
      >
        <manual-balances-form
          ref="dialogChild"
          :edit="balanceToEdit"
        ></manual-balances-form>
      </big-dialog>
      <manual-balances-list @editBalance="edit($event)"></manual-balances-list>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import ManualBalancesForm from '@/components/accounts/ManualBalancesForm.vue';
import ManualBalancesList from '@/components/accounts/ManualBalancesList.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import { ManualBalance } from '@/services/types-model';

@Component({
  components: { ManualBalancesList, ManualBalancesForm, BigDialog }
})
export default class ManualBalances extends Vue {
  balanceToEdit: ManualBalance | null = null;
  dialogTitle: string = '';
  dialogSubTitle: string = '';
  openDialog: boolean = false;

  newBalance() {
    this.dialogTitle = 'Add Manual Balance';
    this.dialogSubTitle = '';
    this.openDialog = true;
  }
  edit(balance: ManualBalance) {
    this.balanceToEdit = balance;
    this.dialogTitle = 'Edit Manual Balance';
    this.dialogSubTitle = 'Modify balance amount, location, and tags';
    this.openDialog = true;
  }

  async save() {
    interface dataForm extends Vue {
      save(): Promise<boolean>;
    }
    const form = this.$refs.dialogChild as dataForm;
    form.save().then(success => {
      if (success === true) this.openDialog = false;
    });
  }
}
</script>

<style scoped></style>
