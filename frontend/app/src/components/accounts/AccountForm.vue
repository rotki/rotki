<template>
  <v-form ref="form" :value="value" @input="input">
    <v-row no-gutters>
      <v-col cols="12">
        <v-select
          v-model="blockchain"
          class="account-form__chain"
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
      </v-col>
    </v-row>
    <v-row v-if="!edit" no-gutters>
      <v-col cols="12">
        <input-mode-select v-model="inputMode" :blockchain="blockchain" />
      </v-col>
    </v-row>
    <v-row v-if="displayXpubInput" align="center" no-gutters class="mt-2">
      <v-col cols="auto">
        <v-select
          v-model="xpubKeyType"
          class="account-form__xpub-key-type"
          item-value="value"
          item-text="label"
          :disabled="accountOperation || loading || !!edit"
          :items="keyType"
        />
      </v-col>
      <v-col>
        <v-text-field
          v-model="xpub"
          class="account-form__xpub"
          :label="$t('account_form.labels.btc.xpub')"
          autocomplete="off"
          :disabled="accountOperation || loading || !!edit"
          @paste="onPasteXpub"
        />
      </v-col>
      <v-col cols="auto">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn icon v-bind="attrs" v-on="on" @click="advanced = !advanced">
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
    <v-row v-if="isBtc && isXpub && advanced" no-gutters>
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
    <v-row no-gutters class="mt-2">
      <v-col cols="12">
        <v-text-field
          v-if="(!isBtc || (isBtc && !isXpub) || !!edit) && !isMetaMask"
          v-model="address"
          class="account-form__address"
          :label="$t('account_form.labels.account')"
          :rules="rules"
          :error-messages="errorMessages"
          autocomplete="off"
          :disabled="accountOperation || loading || !!edit"
          @paste="onPasteAddress"
        />
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col cols="12">
        <v-text-field
          v-model="label"
          class="account-form__label"
          :label="$t('account_form.labels.label')"
          :disabled="accountOperation || loading"
        />
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col cols="12">
        <tag-input v-model="tags" :disabled="accountOperation || loading" />
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col cols="12">
        <div class="account-form--progress">
          <v-progress-linear v-if="accountOperation" indeterminate />
        </div>
      </v-col>
    </v-row>
  </v-form>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import {
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/components/accounts/const';
import InputModeSelect from '@/components/accounts/InputModeSelect.vue';
import { AccountInput } from '@/components/accounts/types';
import TagInput from '@/components/inputs/TagInput.vue';
import { TaskType } from '@/model/task-type';
import { deserializeApiErrorMessage } from '@/services/converters';
import {
  AddAccountsPayload,
  BlockchainAccount,
  BlockchainAccountPayload,
  XpubPayload
} from '@/store/balances/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { Message } from '@/store/types';
import {
  Blockchain,
  BTC,
  ETH,
  GeneralAccount,
  SupportedBlockchains
} from '@/typing/types';
import { trimOnPaste } from '@/utils/event';
import { getMetamaskAddresses } from '@/utils/metamask';

type ValidationRule = (value: string) => boolean | string;
type XpubType = {
  readonly label: string;
  readonly value: string;
};

const XPUB_LABEL = 'P2PKH';
const XPUB_VALUE = 'xpub';
const YPUB_LABEL = 'P2SH-P2WPKH';
const YPUB_VALUE = 'ypub';
const ZPUB_LABEL = 'WPKH';
const ZPUB_VALUE = 'zpub';

const XPUB_KEY_TYPE = [XPUB_VALUE, YPUB_VALUE, ZPUB_VALUE] as const;

type XpubKeyType = typeof XPUB_KEY_TYPE[number];

@Component({
  components: { InputModeSelect, TagInput },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('balances', ['account'])
  },
  methods: {
    ...mapActions('balances', ['addAccounts', 'editAccount', 'addAccount'])
  }
})
export default class AccountForm extends Vue {
  readonly items = SupportedBlockchains;
  isTaskRunning!: (type: TaskType) => boolean;
  blockchain: Blockchain = ETH;
  pending: boolean = false;
  xpub: string = '';
  derivationPath: string = '';
  address: string = '';
  label: string = '';
  tags: string[] = [];
  errorMessages: string[] = [];
  xpubKeyType: XpubKeyType = XPUB_VALUE;
  account!: (address: string) => GeneralAccount | undefined;
  addAccount!: (payload: BlockchainAccountPayload) => Promise<void>;
  addAccounts!: (payload: AddAccountsPayload) => Promise<void>;
  editAccount!: (payload: BlockchainAccountPayload) => Promise<void>;
  advanced: boolean = false;
  inputMode: AccountInput = MANUAL_ADD;

  get isBtc(): boolean {
    return this.blockchain === BTC;
  }

  get isXpub(): boolean {
    return this.inputMode === XPUB_ADD;
  }

  get isMetaMask(): boolean {
    return this.inputMode === METAMASK_IMPORT;
  }

  get displayXpubInput(): boolean {
    const edit = !!this.edit;
    return (!edit && this.isBtc && this.isXpub) || (edit && !!this.xpub);
  }

  get keyType(): XpubType[] {
    return [
      {
        label: XPUB_LABEL,
        value: XPUB_VALUE
      },
      {
        label: YPUB_LABEL,
        value: YPUB_VALUE
      },
      {
        label: ZPUB_LABEL,
        value: ZPUB_VALUE
      }
    ];
  }

  get rules(): ValidationRule[] {
    const rules: ValidationRule[] = [];
    if (this.isMetaMask) {
      return rules;
    }
    rules.push(this.nonEmptyRule);
    if (!this.edit) {
      rules.push(this.checkIfExists);
    }
    return rules;
  }

  private nonEmptyRule(value: string): boolean | string {
    return !!value || this.$tc('account_form.validation.address_non_empty');
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
      return;
    }

    this.address = this.edit.address;
    this.blockchain = this.edit.chain;
    this.label = this.edit.label;
    this.tags = this.edit.tags;
    if ('xpub' in this.edit) {
      const match = this.edit.xpub.match(/([xzy]pub)(.*)/);
      if (match) {
        this.xpub = match[0];
        this.xpubKeyType = match[1] as XpubKeyType;
      } else {
        this.xpub = this.edit.xpub;
      }

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

  @Watch('blockchain')
  onBlockchainChanged() {
    if (this.isBtc) {
      this.inputMode = XPUB_ADD;
    } else {
      this.inputMode = MANUAL_ADD;
    }
  }

  @Watch('xpub')
  onXpubChange(value: string) {
    if (!value) {
      return;
    }
    this.setXpubKeyType(value);
  }

  private setXpubKeyType(value: string) {
    const match = AccountForm.isPrefixed(value);
    if (match && match.length === 3) {
      this.xpubKeyType = match[1] as XpubKeyType;
    }
  }

  private static isPrefixed(value: string) {
    return value.match(/([xzy]pub)(.*)/);
  }

  onPasteAddress(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.address = paste;
    }
  }

  onPasteXpub(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.setXpubKeyType(paste);
      this.xpub = paste;
    }
  }

  reset() {
    this.address = '';
    this.label = '';
    this.tags = [];
    this.xpub = '';
    this.derivationPath = '';
    (this.$refs.form as any).resetValidation();
    this.blockchain = ETH;
    this.inputMode = MANUAL_ADD;
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

  async metamaskImport(): Promise<boolean> {
    try {
      let addresses: string[];
      if (this.$interop.isPackaged) {
        addresses = await this.$interop.metamaskImport();
      } else {
        addresses = await getMetamaskAddresses();
      }

      const payload = addresses.map(value => ({
        address: value,
        label: this.label,
        tags: this.tags
      }));

      await this.addAccounts({
        blockchain: ETH,
        payload: payload
      });
      return true;
    } catch (e) {
      const title = this.$tc('blockchain_balances.metamask_import.error.title');
      const description = this.$tc(
        'blockchain_balances.metamask_import.error.description',
        0,
        {
          error: e.message
        }
      );
      notify(description, title, Severity.ERROR, true);
      return false;
    }
  }

  payload(): BlockchainAccountPayload {
    let xpubPayload: XpubPayload | undefined;
    if (this.isBtc && this.isXpub) {
      const xpubKey = this.xpub.trim();
      const xpub = AccountForm.isPrefixed(xpubKey)
        ? xpubKey
        : `${this.xpubKeyType}${xpubKey}`;
      xpubPayload = {
        xpub: xpub,
        derivationPath: this.derivationPath ?? undefined
      };
    } else {
      xpubPayload = undefined;
    }

    return {
      blockchain: this.blockchain,
      address: this.address.trim(),
      label: this.label,
      tags: this.tags,
      xpub: xpubPayload
    };
  }

  async manualAdd() {
    const payload = this.payload();
    try {
      if (this.edit) {
        await this.editAccount(payload);
      } else {
        await this.addAccount(payload);
      }

      this.reset();
    } catch (e) {
      const apiErrorMessage = deserializeApiErrorMessage(e.message);
      if (apiErrorMessage) {
        const fields = ['address', 'xpub'];
        let errors: string[] = [];
        this.clearErrors();
        for (const field in fields) {
          if (!(field in apiErrorMessage)) {
            continue;
          }
          errors = errors.concat(apiErrorMessage[field]);
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
    return true;
  }

  async save(): Promise<boolean> {
    let result: boolean;
    this.pending = true;

    if (this.isMetaMask) {
      result = await this.metamaskImport();
    } else {
      result = await this.manualAdd();
    }

    this.pending = false;
    return result;
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
.account-form {
  &__xpub-key-type {
    max-width: 150px;
  }

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
