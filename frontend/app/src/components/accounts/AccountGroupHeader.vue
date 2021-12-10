<template>
  <td v-if="!group" class="font-weight-medium" colspan="5" :class="mobileClass">
    {{ $t('account_group_header.standalone') }}
  </td>
  <fragment v-else>
    <td
      :colspan="$vuetify.breakpoint.xsOnly ? 1 : 2"
      :class="{
        'v-data-table__mobile-row': $vuetify.breakpoint.xsOnly,
        'pa-2': !$vuetify.breakpoint.xsOnly
      }"
    >
      <div class="ps-8">
        <span class="text-subtitle-2">{{ label }}</span>
      </div>
      <div>
        <v-btn
          v-if="items.length > 0"
          small
          icon
          @click="expandClicked({ ...xpub, balance })"
        >
          <v-icon v-if="expanded" small>mdi-chevron-up</v-icon>
          <v-icon v-else small>mdi-chevron-down</v-icon>
        </v-btn>
        <v-btn v-else small icon disabled />
        <span class="font-weight-medium">
          {{ $t('account_group_header.xpub') }}
        </span>
        <span :style="amountPrivacyStyle">
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
        <span v-if="xpub.derivationPath" :style="amountPrivacyStyle">
          <span class="font-weight-medium">
            {{ $t('account_group_header.derivation_path') }}
          </span>
          {{ xpub.derivationPath }}
        </span>
      </div>
      <tag-display wrapper-class="mt-1 ms-8" :tags="xpubTags" />
    </td>
    <td class="text-end" :class="mobileClass">
      <amount-display
        :value="sum"
        :loading="loading"
        :asset="$vuetify.breakpoint.xsOnly ? 'BTC' : null"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <amount-display
        fiat-currency="USD"
        show-currency="symbol"
        :value="usdSum"
        :loading="loading"
      />
    </td>
    <td class="text-end" :class="mobileClass">
      <v-tooltip top>
        <template #activator="{ on, attrs }">
          <v-btn
            small
            v-bind="attrs"
            icon
            :disabled="false"
            class="mx-1"
            v-on="on"
            @click="editClicked(xpub)"
          >
            <v-icon small> mdi-pencil-outline </v-icon>
          </v-btn>
        </template>
        <span>{{ $t('account_group_header.edit_tooltip') }}</span>
      </v-tooltip>
      <v-tooltip top open-delay="400">
        <template #activator="{ on }">
          <v-btn small icon class="mr-1" v-on="on" @click="deleteClicked(xpub)">
            <v-icon small>mdi-delete-outline</v-icon>
          </v-btn>
        </template>
        <span> {{ $t('account_group_header.delete_tooltip') }} </span>
      </v-tooltip>
    </td>
  </fragment>
</template>
<script lang="ts">
import { Balance, BigNumber } from '@rotki/common';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import CopyButton from '@/components/helper/CopyButton.vue';
import Fragment from '@/components/helper/Fragment';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { balanceSum, truncateAddress, truncationPoints } from '@/filters';
import PrivacyMixin from '@/mixins/privacy-mixin';
import { XpubAccountWithBalance } from '@/store/balances/types';
import { balanceUsdValueSum } from '@/store/defi/utils';

@Component({
  components: { TagDisplay, CopyButton, Fragment }
})
export default class AccountGroupHeader extends Mixins(PrivacyMixin) {
  @Prop({ required: true, type: String })
  group!: string;
  @Prop({ required: true, type: Array })
  items!: XpubAccountWithBalance[];
  @Prop({ required: true, type: Boolean })
  expanded!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  loading!: boolean;

  get mobileClass(): string | null {
    return this.$vuetify.breakpoint.xsOnly ? 'v-data-table__mobile-row' : null;
  }

  get xpub(): XpubAccountWithBalance {
    return this.items.filter(item => !item.address)[0];
  }

  get label(): string {
    return this.xpub.label;
  }

  get xpubTags(): string[] {
    return this.xpub.tags;
  }

  get displayXpub(): string {
    return truncateAddress(
      this.xpub.xpub,
      truncationPoints[this.$vuetify.breakpoint.name] ?? 4
    );
  }

  get sum(): BigNumber {
    return balanceSum(this.items.map(({ balance: { amount } }) => amount));
  }

  get usdSum(): BigNumber {
    return balanceUsdValueSum(this.items);
  }

  get balance(): Balance {
    return { amount: this.sum, usdValue: this.usdSum };
  }

  @Emit()
  deleteClicked(_payload: XpubAccountWithBalance) {}

  @Emit()
  expandClicked(_xpub: XpubAccountWithBalance) {}

  @Emit()
  editClicked(_xpub: XpubAccountWithBalance) {}
}
</script>
