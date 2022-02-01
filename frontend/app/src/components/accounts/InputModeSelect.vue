<template>
  <div class="mb-5">
    <v-btn-toggle
      :value="value"
      class="input-mode-select"
      mandatory
      @change="input($event)"
    >
      <v-btn :value="MANUAL_ADD" data-cy="input-mode-manual">
        <v-icon>mdi-pencil-plus</v-icon>
        <span class="hidden-sm-and-down ml-1">
          {{ $t('input_mode_select.manual_add.label') }}
        </span>
      </v-btn>
      <v-btn
        v-if="isEth"
        :value="METAMASK_IMPORT"
        :disabled="!isMetaMaskSupported()"
      >
        <v-img
          contain
          max-width="24px"
          :src="require(`@/assets/images/metamask-fox.svg`)"
        />
        <span class="hidden-sm-and-down ml-1">
          {{ $t('input_mode_select.metamask_import.label') }}
        </span>
      </v-btn>
      <v-btn v-if="isBtc" :value="XPUB_ADD">
        <v-icon>mdi-key-plus</v-icon>
        <span class="hidden-sm-and-down ml-1">
          {{ $t('input_mode_select.xpub_add.label') }}
        </span>
      </v-btn>
    </v-btn-toggle>
    <p
      v-if="isEth && isMetaMask"
      class="mt-3 info--text text-caption"
      v-text="$t('input_mode_select.metamask_import.metamask')"
    />
    <p
      v-if="isEth && !isMetaMaskSupported()"
      class="mt-3 warning--text text-caption"
      v-text="$t('input_mode_select.metamask_import.missing')"
    />
  </div>
</template>

<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  toRefs,
  unref
} from '@vue/composition-api';
import {
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/components/accounts/const';
import { AccountInput } from '@/components/accounts/types';
import { isMetaMaskSupported } from '@/utils/metamask';

export default defineComponent({
  props: {
    blockchain: {
      required: true,
      type: String as PropType<Blockchain>,
      validator: (value: any) => Object.values(Blockchain).includes(value)
    },
    value: { required: true, type: String as PropType<AccountInput> }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { blockchain, value } = toRefs(props);

    const input = (value: AccountInput) => emit('input', value);

    const isEth = computed(() => blockchain.value === Blockchain.ETH);
    const isBtc = computed(() => blockchain.value === Blockchain.BTC);
    const isMetaMask = computed(() => unref(value) === METAMASK_IMPORT);

    return {
      MANUAL_ADD,
      XPUB_ADD,
      METAMASK_IMPORT,
      isEth,
      isBtc,
      isMetaMask,
      isMetaMaskSupported,
      input
    };
  }
});
</script>
