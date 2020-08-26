<template>
  <v-row>
    <v-col cols="12">
      <v-select
        v-model="selected"
        class="blockchain-balances__chain"
        :items="items"
        label="Choose blockchain"
        :disabled="accountOperation || loading || !!edit"
      ></v-select>
      <v-text-field
        v-model="address"
        class="blockchain-balances__address"
        label="Account"
        :error-messages="errorMessages"
        :disabled="accountOperation || loading || !!edit"
      ></v-text-field>
      <v-text-field
        v-model="label"
        class="blockchain-balances__label"
        label="Label"
        :disabled="accountOperation || loading"
      ></v-text-field>
      <tag-input
        v-model="tags"
        :disabled="accountOperation || loading"
      ></tag-input>
      <div class="blockchain-balances--progress">
        <v-progress-linear
          v-if="accountOperation"
          indeterminate
        ></v-progress-linear>
      </div>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import TagInput from '@/components/inputs/TagInput.vue';
import { TaskType } from '@/model/task-type';
import { deserializeApiErrorMessage } from '@/services/converters';
import { BlockchainAccountPayload } from '@/store/balances/actions';
import { Message } from '@/store/types';
import { Account, Blockchain, SupportedBlockchains } from '@/typing/types';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
const { mapGetters } = createNamespacedHelpers('balances');
@Component({
  components: { TagInput },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapGetters(['accountTags', 'accountLabel'])
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

  accountTags!: (blockchain: Blockchain, address: string) => string[];
  accountLabel!: (blockchain: Blockchain, address: string) => string;
  @Prop({ required: false, default: null })
  edit!: Account | null;

  private setEditMode() {
    if (!this.edit) {
      this.address = '';
      return;
    }
    const { address, chain } = this.edit;
    this.address = address;
    this.selected = chain;
    this.label = this.accountLabel(this.selected, address);
    this.tags = this.accountTags(this.selected, address);
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

  @Emit()
  editComplete() {
    this.address = '';
    this.label = '';
    this.tags = [];
  }

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
      this.editComplete();
    } catch (e) {
      const apiErrorMessage = deserializeApiErrorMessage(e.message);
      if (apiErrorMessage && 'address' in apiErrorMessage) {
        this.clearErrors();
        this.errorMessages.push(...apiErrorMessage['address']);
        this.pending = false;
        return false;
      }
      this.$store.commit('setMessage', {
        description: `Error while adding account: ${e}`,
        title: 'Adding Account',
        success: false
      } as Message);
      return false;
    }
    this.pending = false;
    return true;
  }

  private clearErrors() {
    for (let i = 0; i < this.errorMessages.length; i++) {
      this.errorMessages.pop();
    }
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
