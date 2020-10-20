<template>
  <fragment>
    <v-btn-toggle
      :value="value"
      class="input-mode-select"
      mandatory
      @change="input($event)"
    >
      <v-btn :value="MANUAL_ADD">
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
      class="mt-3 info--text caption"
      v-text="$t('input_mode_select.metamask_import.metamask')"
    />
    <p
      v-if="isEth && !isMetaMaskSupported()"
      class="mt-3 warning--text caption"
      v-text="$t('input_mode_select.metamask_import.missing')"
    />
  </fragment>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import {
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/components/accounts/const';
import { AccountInput } from '@/components/accounts/types';
import Fragment from '@/components/helper/Fragment';
import { Blockchain, BTC, ETH, SupportedBlockchains } from '@/typing/types';
import { isMetaMaskSupported } from '@/utils/metamask';

@Component({
  components: { Fragment }
})
export default class InputModeSelect extends Vue {
  @Prop({
    required: true,
    type: String,
    validator: (value: any) => SupportedBlockchains.includes(value)
  })
  blockchain!: Blockchain;

  @Prop({ required: true })
  value!: AccountInput;

  readonly MANUAL_ADD = MANUAL_ADD;
  readonly METAMASK_IMPORT = METAMASK_IMPORT;
  readonly XPUB_ADD = XPUB_ADD;
  readonly isMetaMaskSupported = isMetaMaskSupported;

  get isEth(): boolean {
    return this.blockchain === ETH;
  }

  get isBtc(): boolean {
    return this.blockchain === BTC;
  }

  get isMetaMask(): boolean {
    return this.value === METAMASK_IMPORT;
  }

  @Emit()
  input(_value: AccountInput) {}
}
</script>

<style scoped lang="scss"></style>
