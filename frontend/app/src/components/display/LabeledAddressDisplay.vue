<template>
  <div>
    <v-tooltip top>
      <template #activator="{ on }">
        <span class="labeled-address-display__address" v-on="on">
          <v-chip label outlined>
            <span v-if="account.identifier !== account.account" class="pr-1">
              {{
                $t('labeled_address_display.identifier', {
                  identifier: account.identifier
                })
              }}
            </span>
            <span :class="privacyMode ? 'blur-content' : null">
              {{ address | truncateAddress }}
            </span>
          </v-chip>
        </span>
      </template>
      <span> {{ address }} </span>
    </v-tooltip>
    <v-tooltip top>
      <template #activator="{ on, attrs }">
        <v-btn
          x-small
          v-bind="attrs"
          icon
          class="ml-2"
          v-on="on"
          @click="copy(address)"
        >
          <v-icon>mdi-content-copy</v-icon>
        </v-btn>
      </template>
      <span>{{ $t('labeled_address_display.copy') }}</span>
    </v-tooltip>
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { randomHex } from '@/typing/utils';

type Account = { readonly identifier: string; readonly account: string };

@Component({
  computed: { ...mapState('session', ['privacyMode']) }
})
export default class LabeledAddressDisplay extends Mixins(ScrambleMixin) {
  privacyMode!: boolean;

  @Prop({ required: true })
  account!: Account;

  get address(): string {
    return this.scrambleData ? randomHex() : this.account.account;
  }

  copy(address: string) {
    navigator.clipboard.writeText(address);
  }
}
</script>

<style scoped lang="scss">
.labeled-address-display {
  &__address {
    font-weight: 500;
    padding-top: 6px;
    padding-bottom: 6px;
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
