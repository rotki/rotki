<template>
  <td v-if="!group" class="font-weight-medium" colspan="5">
    {{ $t('account_group_header.standalone') }}
  </td>
  <fragment v-else>
    <td>
      <v-btn v-if="items.length > 0" small icon @click="expandClicked(xpub)">
        <v-icon v-if="expanded" small>mdi-chevron-up</v-icon>
        <v-icon v-else small>mdi-chevron-down</v-icon>
      </v-btn>
      <v-btn v-else small icon disabled />
      <span class="font-weight-medium">
        {{ $t('account_group_header.xpub') }}
      </span>
      <span :style="privacyStyle">
        <v-tooltip top open-delay="400">
          <template #activator="{ on }">
            <span v-on="on">{{ displayXpub }}</span>
          </template>
          <span> {{ xpub.xpub }} </span>
        </v-tooltip>
      </span>
      <copy-button
        :value="xpub.xpub"
        :tooltip="$t('account_group_header.copy_tooltip')"
      />
      <span v-if="xpub.derivationPath" :style="privacyStyle">
        <span class="font-weight-medium">
          {{ $t('account_group_header.derivation_path') }}
        </span>
        {{ xpub.derivationPath }}
      </span>
    </td>
    <td class="text-end">
      <amount-display :value="sum" />
    </td>
    <td class="text-end">
      <amount-display
        fiat-currency="USD"
        show-currency="symbol"
        :value="usdSum"
      />
    </td>
    <td class="text-end">
      <v-tooltip top open-delay="400">
        <template #activator="{ on }">
          <v-btn small icon class="mr-1" v-on="on" @click="deleteClicked(xpub)">
            <v-icon small>mdi-delete-outline</v-icon>
          </v-btn>
        </template>
        <span> {{ $t('account_group_header.delete_tooltip') }} </span>
      </v-tooltip>
    </td>
    <td />
  </fragment>
</template>
<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import CopyButton from '@/components/helper/CopyButton.vue';
import Fragment from '@/components/helper/Fragment';
import { balanceSum, truncateAddress, truncationPoints } from '@/filters';
import PrivacyMixin from '@/mixins/privacy-mixin';
import { XpubAccountWithBalance, XpubPayload } from '@/store/balances/types';
import { balanceUsdValueSum } from '@/store/defi/utils';

@Component({
  components: { CopyButton, Fragment }
})
export default class AccountGroupHeader extends Mixins(PrivacyMixin) {
  @Prop({ required: true, type: String })
  group!: string;
  @Prop({ required: true, type: Array })
  items!: XpubAccountWithBalance[];
  @Prop({ required: true, type: Boolean })
  expanded!: boolean;

  get displayXpub(): string {
    return truncateAddress(
      this.xpub.xpub,
      truncationPoints[this.$vuetify.breakpoint.name] ?? 4
    );
  }

  get xpub(): XpubPayload {
    const split = this.group.split(':');
    return {
      xpub: split[0],
      derivationPath: split[1]
    };
  }

  get sum(): BigNumber {
    return balanceSum(this.items.map(({ balance: { amount } }) => amount));
  }

  get usdSum(): BigNumber {
    return balanceUsdValueSum(this.items);
  }

  @Emit()
  deleteClicked(_payload: XpubPayload) {}

  @Emit()
  expandClicked(_xpub: XpubPayload) {}
}
</script>
