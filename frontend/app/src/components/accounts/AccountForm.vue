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
        <v-radio-group
          v-if="isBtc"
          v-model="btcAccountType"
          :label="$t('account_form.labels.btc.account_type')"
          row
          :disabled="!!edit"
        >
          <v-radio value="xpub" :label="$t('account_form.labels.btc.xpub')" />
          <v-radio
            value="standalone"
            :label="$t('account_form.labels.btc.standalone')"
          />
        </v-radio-group>
        <v-row v-if="isBtc && isXpub" align="center" no-gutters>
          <v-col>
            <v-text-field
              v-model="xpub"
              class="account-form__xpub"
              :label="$t('account_form.labels.btc.xpub')"
              autocomplete="off"
              :disabled="accountOperation || loading || !!edit"
            />
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  icon
                  v-bind="attrs"
                  v-on="on"
                  @click="advanced = !advanced"
                >
                  <v-icon v-if="advanced">mdi-chevron-up</v-icon>
                  <v-icon v-else>mdi-chevron-down</v-icon>
                </v-btn>
              </template>
              <span>
                {{ $tc('account_form.advanced_tooltip', advanced ? 0 : 1) }}
              </span>
            </v-tooltip>
          </v-col>
        </v-row>

        <v-row v-if="isBtc && btcAccountType === 'xpub' && advanced" no-gutters>
          <v-col>
            <v-text-field
              v-model="derivationPath"
              class="account-form__derivation-path"
              :label="$t('account_form.labels.btc.derivation_path')"
              autocomplete="off"
              :disabled="accountOperation || loading || !!edit"
              persistent-hint
              :hint="$t('account_form.labels.btc.derivation_path_hint')"
            />
          </v-col>
        </v-row>

        <v-text-field
          v-if="!isBtc || ((isBtc && btcAccountType !== 'xpub') || !!edit)"
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
import {
  BlockchainAccountPayload,
  BlockchainAccount
} from '@/store/balances/types';
import { Message } from '@/store/types';
import {
  Blockchain,
  BTC,
  ETH,
  GeneralAccount,
  SupportedBlockchains
} from '@/typing/types';

type ValidationRule = (value: string) => boolean | string;

@Component({
  components: { TagInput },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('balances', ['account'])
  }
})
export default class AccountForm extends Vue {
  readonly items = SupportedBlockchains;
  isTaskRunning!: (type: TaskType) => boolean;
  selected: Blockchain = ETH;
  pending: boolean = false;
  xpub: string = '';
  derivationPath: string = '';
  address: string = '';
  label: string = '';
  tags: string[] = [];
  errorMessages: string[] = [];
  account!: (address: string) => GeneralAccount | undefined;
  advanced: boolean = false;

  btcAccountType: 'xpub' | 'standalone' = 'xpub';

  get isBtc(): boolean {
    return this.selected === BTC;
  }

  get isXpub(): boolean {
    return this.btcAccountType === 'xpub';
  }

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
  edit!: BlockchainAccount | null;
  @Prop({ required: true, type: Boolean, default: false })
  value!: boolean;

  private setEditMode() {
    if (!this.edit) {
      this.address = '';
      return;
    }

    this.address = this.edit.address;
    this.selected = this.edit.chain;
    this.label = this.edit.label;
    this.tags = this.edit.tags;
    if ('xpub' in this.edit) {
      this.xpub = this.edit.xpub;
      this.derivationPath = this.edit.derivationPath;
    }
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
    this.xpub = '';
    this.derivationPath = '';
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
      const xpubPayload =
        this.isBtc && this.btcAccountType === 'xpub'
          ? {
              xpub: this.xpub,
              derivationPath: this.derivationPath ?? undefined
            }
          : undefined;
      const payload: BlockchainAccountPayload = {
        blockchain: this.selected,
        address: this.address,
        label: this.label,
        tags: this.tags,
        xpub: xpubPayload
      };

      await this.$store.dispatch(
        this.edit ? 'balances/editAccount' : 'balances/addAccount',
        payload
      );
      this.reset();
    } catch (e) {
      const apiErrorMessage = deserializeApiErrorMessage(e.message);
      if (apiErrorMessage) {
        const fields = ['address', 'xpub'];
        const errors: string[] = [];
        this.clearErrors();
        for (const field in fields) {
          if (!(field in apiErrorMessage)) {
            continue;
          }
          errors.concat(apiErrorMessage[field]);
        }
        this.setErrors(errors);
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
