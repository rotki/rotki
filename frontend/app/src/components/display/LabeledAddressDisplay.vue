<template>
  <div>
    <v-tooltip top open-delay="400" :disabled="!truncated">
      <template #activator="{ on }">
        <span class="labeled-address-display__address" v-on="on">
          <v-chip label outlined>
            <span v-if="!!account.label" class="pr-1">
              {{
                $t('labeled_address_display.label', {
                  label: account.label
                })
              }}
            </span>
            <span :class="privacyMode ? 'blur-content' : null">
              {{ displayAddress }}
            </span>
          </v-chip>
        </span>
      </template>
      <span> {{ address }} </span>
    </v-tooltip>
    <div class="labeled-address-display__copy">
      <v-tooltip top open-delay="400">
        <template #activator="{ on, attrs }">
          <v-btn
            small
            v-bind="attrs"
            tile
            icon
            v-on="on"
            @click="copy(address)"
          >
            <v-icon small>mdi-content-copy</v-icon>
          </v-btn>
        </template>
        <span>{{ $t('labeled_address_display.copy') }}</span>
      </v-tooltip>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { truncateAddress, truncationPoints } from '@/filters';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { GeneralAccount } from '@/typing/types';
import { randomHex } from '@/typing/utils';

@Component({
  computed: { ...mapState('session', ['privacyMode']) }
})
export default class LabeledAddressDisplay extends Mixins(ScrambleMixin) {
  privacyMode!: boolean;

  @Prop({ required: true })
  account!: GeneralAccount;

  truncated: boolean = false;

  get address(): string {
    return this.scrambleData ? randomHex() : this.account.address;
  }

  get displayAddress(): string {
    const address = truncateAddress(
      this.address,
      truncationPoints[this.$vuetify.breakpoint.name] ?? 4
    );
    this.truncated = address.includes('...');
    return address;
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
    background-color: white;

    ::v-deep {
      .v-chip {
        &--label {
          border-top-right-radius: 0 !important;
          border-bottom-right-radius: 0 !important;
        }
      }
    }
  }

  &__copy {
    display: inline-block;
    background-color: var(--v-rotki-light-grey-base);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-left-width: 0;
    border-radius: 0 4px 4px 0;

    button {
      height: 30px;
      width: 30px;
    }
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
