<template>
  <v-row>
    <v-col cols="12">
      <v-select
        v-model="selected"
        class="blockchain-balances__chain"
        :items="items"
        label="Choose blockchain"
        :disabled="accountOperation"
      ></v-select>
      <v-text-field
        v-model="accountAddress"
        class="blockchain-balances__address"
        label="Account"
        :disabled="accountOperation"
      ></v-text-field>
      <v-text-field
        v-model="accountLabel"
        class="blockchain-balances__label"
        label="Label"
        :disabled="accountOperation"
      ></v-text-field>
      <tag-input
        v-model="tags"
        :disabled="accountOperation"
        @remove="removeTag($event)"
      ></tag-input>
      <div class="blockchain-balances--progress">
        <v-progress-linear
          v-if="accountOperation"
          indeterminate
        ></v-progress-linear>
      </div>
      <v-btn
        class="blockchain-balances__buttons__add"
        depressed
        color="primary"
        type="submit"
        :disabled="!accountAddress || accountOperation"
        @click="addAccount"
      >
        Add
      </v-btn>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import {
  Blockchain,
  Severity,
  SupportedBlockchains,
  Tag
} from '@/typing/types';
import { TaskType } from '@/model/task';
import { notify } from '@/store/notifications/utils';
import { createNamespacedHelpers } from 'vuex';
import TagInput from '@/components/inputs/TagInput.vue';
import TagManager from '@/components/tags/TagManager.vue';

const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');
@Component({
  components: { TagManager, TagInput },
  computed: {
    ...mapTaskGetters(['isTaskRunning'])
  }
})
export default class AccountForm extends Vue {
  readonly items: string[] = SupportedBlockchains;
  isTaskRunning!: (type: TaskType) => boolean;
  selected: Blockchain = 'ETH';
  pending: boolean = false;
  accountAddress: string = '';
  accountLabel: string = '';
  tags: string[] = [];

  get accountOperation(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT) ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT) ||
      this.pending
    );
  }

  removeTag(tag: Tag) {
    const index = this.tags.findIndex(tagName => tagName === tag.name);
    if (index > -1) {
      const tags = [...this.tags];
      tags.splice(index, 1);
      this.tags = tags;
    }
  }

  async addAccount() {
    this.pending = true;
    try {
      await this.$store.dispatch('balances/addAccount', {
        blockchain: this.selected,
        address: this.accountAddress,
        label: this.accountLabel,
        tags: this.tags
      });
      this.accountAddress = '';
      this.accountLabel = '';
      this.tags = [];
    } catch (e) {
      notify(
        `Error while adding account: ${e}`,
        'Adding Account',
        Severity.ERROR
      );
    }
    this.pending = false;
  }
}
</script>
<style scoped lang="scss">
.blockchain-balances--progress {
  height: 15px;
}
</style>
