<template>
  <v-form ref="form" :value="value" @input="input">
    <v-row>
      <v-col cols="12">
        <v-select
          v-model="selected"
          class="blockchain-balances__chain"
          :items="items"
          :label="$t('account_form.labels.blockchain')"
          :disabled="accountOperation || loading || !!edit"
        >
          <template #selection="{ item }">
            <asset-details class="pt-2 pb-2" :asset="item" />
          </template>
          <template #item="{ item }">
            <asset-details class="pt-2 pb-2" :asset="item" />
          </template>
        </v-select>
        <v-text-field
          v-model="address"
          class="blockchain-balances__address"
          :label="$t('account_form.labels.account')"
          :rules="rules"
          :error-messages="errorMessages"
          autocomplete="off"
          :disabled="accountOperation || loading || !!edit"
        />
        <v-text-field
          v-model="label"
          class="blockchain-balances__label"
          :label="$t('account_form.labels.label')"
          :disabled="accountOperation || loading"
        />
        <tag-input v-model="tags" :disabled="accountOperation || loading" />
        <div class="blockchain-balances--progress">
          <v-progress-linear v-if="accountOperation" indeterminate />
        </div>
      </v-col>
    </v-row>
  </v-form>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import TagInput from '@/components/inputs/TagInput.vue';
import { TaskType } from '@/model/task-type';
import { deserializeApiErrorMessage } from '@/services/converters';
import { BlockchainAccountPayload } from '@/store/balances/actions';
import { Message } from '@/store/types';
import {
  Account,
  Blockchain,
  GeneralAccount,
  SupportedBlockchains
} from '@/typing/types';
import { assert } from '@/utils/assertions';

type ValidationRule = (value: string) => boolean | string;
@Component({
  components: { TagInput },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('balances', ['account'])
  }
})
export default class AccountForm extends Vue {
  readonly items: string[] = SupportedBlockchains;
  isTaskRunning!: (type: TaskType) => boolean;
  selected: Blockchain = 'ETH';
  pending: boolean = false;
  address: string = '';
  label: string = '';
  tags: string[] = [];
  errorMessages: string[] = [];
  account!: (address: string) => GeneralAccount | undefined;

  get rules(): ValidationRule[] {
    const rules: ValidationRule[] = [
      (v: string) =>
        !!v || this.$tc('account_form.validation.address_non_empty')
    ];
    if (!this.edit) {
      rules.push(this.checkIfExists);
    }
    return rules;
  }

  private checkIfExists(value: string): boolean | string {
    return (
      (!!value && !this.account(value)) ||
      this.$tc('account_form.validation.address_exists')
    );
  }

  @Prop({ required: false, default: null })
  edit!: Account | null;
  @Prop({ required: true, type: Boolean, default: false })
  value!: boolean;

  private setEditMode() {
    if (!this.edit) {
      this.address = '';
      return;
    }
    const { address, chain } = this.edit;
    this.address = address;
    this.selected = chain;

    const account = this.account(address);
    assert(account);
    this.label = account.label;
    this.tags = account.tags;
  }

  mounted() {
    this.setEditMode();
  }

  @Watch('address')
  onAddressChanged() {
    if (this.errorMessages.length === 0) {
      return;
    }

    this.clearErrors();
  }

  @Watch('edit')
  onEdit() {
    this.setEditMode();
  }

  reset() {
    this.address = '';
    this.label = '';
    this.tags = [];
    (this.$refs.form as any).resetValidation();
  }

  @Emit()
  input(_valid: boolean) {}

  get accountOperation(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT) ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT) ||
      this.pending
    );
  }

  get loading(): boolean {
    return (
      this.isTaskRunning(TaskType.QUERY_BALANCES) ||
      this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)
    );
  }

  async addAccount(): Promise<boolean> {
    this.pending = true;
    try {
      const payload: BlockchainAccountPayload = {
        blockchain: this.selected,
        address: this.address,
        label: this.label,
        tags: this.tags
      };

      await this.$store.dispatch(
        this.edit ? 'balances/editAccount' : 'balances/addAccount',
        payload
      );
      this.reset();
    } catch (e) {
      const apiErrorMessage = deserializeApiErrorMessage(e.message);
      if (apiErrorMessage && 'address' in apiErrorMessage) {
        this.clearErrors();
        this.setErrors(apiErrorMessage['address']);
        this.pending = false;
        return false;
      }
      this.$store.commit('setMessage', {
        description: this.$tc('account_form.error.description', 0, {
          error: e.message
        }),
        title: this.$tc('account_form.error.title'),
        success: false
      } as Message);
      return false;
    }
    this.pending = false;
    return true;
  }

  private setErrors(errors: string[]) {
    this.errorMessages.push(...errors);
    this.input(false);
  }

  private clearErrors() {
    for (let i = 0; i < this.errorMessages.length; i++) {
      this.errorMessages.pop();
    }
    this.input(true);
  }
}
</script>
<style scoped lang="scss">
.blockchain-balances {
  &__buttons {
    &__cancel {
      margin-left: 8px;
    }
  }

  &--progress {
    height: 15px;
  }
}
</style>
