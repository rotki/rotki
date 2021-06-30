<template>
  <v-dialog
    v-if="!!module"
    max-width="450px"
    :value="!!module"
    @click:outside="closeDialog"
    @close="closeDialog"
  >
    <card outlined-body>
      <template #title>{{ $t('queried_address_dialog.title') }}</template>
      <template #subtitle>
        {{ $t('queried_address_dialog.subtitle', { module: moduleName }) }}
      </template>
      <template #actions>
        <v-row no-gutters align="center" class="flex-nowrap">
          <v-col>
            <blockchain-account-selector
              v-model="account"
              outlined
              flat
              dense
              no-padding
              hide-on-empty-usable
              max-width="340px"
              :usable-addresses="usableAddresses"
              class="queried-address-dialog__selector"
              :chains="['ETH']"
              :label="$t('queried_address_dialog.add')"
            />
          </v-col>
          <v-col cols="auto">
            <v-btn
              icon
              color="primary"
              :disabled="account === null"
              @click="addAddress"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </template>
      <template #details>
        <v-btn icon @click="closeDialog">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </template>
      <div
        v-if="addresses(module).length > 0"
        class="queried-address-dialog__list"
      >
        <v-row
          v-for="address in addresses(module)"
          :key="address"
          no-gutters
          class="py-1"
        >
          <v-col>
            <labeled-address-display
              :account="getAccount(address)"
              class="queried-address-dialog__account"
            />
            <div v-if="getAccount(address).tags.length > 0" class="mt-1">
              <tag-icon
                v-for="tag in getAccount(address).tags"
                :key="tag"
                small
                class="mr-1"
                :tag="tags[tag]"
              />
            </div>
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
                  small
                  icon
                  color="primary"
                  v-bind="attrs"
                  v-on="on"
                  @click="
                    deleteQueriedAddress({
                      module,
                      address
                    })
                  "
                >
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </template>
              <span>{{ $t('queried_address_dialog.remove_tooltip') }}</span>
            </v-tooltip>
          </v-col>
        </v-row>
      </div>
      <div v-else class="queried-address-dialog__empty">
        <div>
          {{
            $t('queried_address_dialog.all_address_queried', {
              module: moduleName
            })
          }}
        </div>
      </div>
    </card>
  </v-dialog>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import {
  QueriedAddresses,
  QueriedAddressPayload,
  SupportedModules
} from '@/services/session/types';
import { Nullable } from '@/types';
import { ETH, GeneralAccount, Tags } from '@/typing/types';
import { assert } from '@/utils/assertions';

@Component({
  name: 'QueriedAddressDialog',
  components: { TagIcon, LabeledAddressDisplay },
  computed: {
    ...mapState('session', ['queriedAddresses', 'tags']),
    ...mapGetters('balances', ['accounts'])
  },
  methods: {
    ...mapActions('session', ['addQueriedAddress', 'deleteQueriedAddress'])
  }
})
export default class QueriedAddressDialog extends Vue {
  @Prop({ required: true })
  module!: Nullable<SupportedModules>;
  queriedAddresses!: QueriedAddresses;
  addQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  deleteQueriedAddress!: (payload: QueriedAddressPayload) => Promise<void>;
  accounts!: GeneralAccount[];
  tags!: Tags;

  account: Nullable<GeneralAccount> = null;

  @Emit('close')
  closeDialog() {
    this.account = null;
  }

  async addAddress() {
    assert(this.module !== null && this.account !== null);
    await this.addQueriedAddress({
      module: this.module,
      address: this.account.address
    });
    this.account = null;
  }

  getAccount(address: string): GeneralAccount | undefined {
    return this.accounts.find(value => value.address === address);
  }

  addresses(module: SupportedModules): string[] {
    return this.queriedAddresses[module] ?? [];
  }

  get usableAddresses(): string[] {
    if (!this.module || this.addresses(this.module).length === 0) {
      return this.accounts
        .filter(({ chain }) => chain === ETH)
        .map(({ address }) => address);
    }
    const addresses = this.addresses(this.module);
    return this.accounts
      .filter(
        ({ chain, address }) => chain === ETH && !addresses.includes(address)
      )
      .map(({ address }) => address);
  }

  get moduleName(): string {
    if (!this.module) {
      return '';
    }
    const defiModule = SUPPORTED_MODULES.find(
      ({ identifier }) => identifier === this.module
    );
    return defiModule?.name ?? this.module;
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.queried-address-dialog {
  &__list {
    overflow-y: scroll;
    overflow-x: hidden;
    width: 99%;
    padding: 8px;
    height: 250px;

    @extend .themed-scrollbar;
  }

  &__empty {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 250px;
  }

  &__account {
    width: 300px;
  }
}

::v-deep {
  .labeled-address-display {
    &__chip {
      max-width: 241px;
    }
  }
}
</style>
