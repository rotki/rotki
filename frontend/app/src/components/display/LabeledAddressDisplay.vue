<template>
  <div class="d-flex flex-row labeled-address-display align-center">
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
    <div class="labeled-address-display__actions">
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
        <v-tooltip top open-delay="600">
          <template #activator="{ on, attrs }">
            <v-btn
              small
              icon
              tile
              v-bind="attrs"
              target="_blank"
              :href="$interop.isPackaged ? undefined : url"
              v-on="on"
              @click="openLink"
            >
              <v-icon small> mdi-launch </v-icon>
            </v-btn>
          </template>
          <span>{{ $t('labeled_address_display.open_link') }}</span>
        </v-tooltip>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { explorerUrls } from '@/components/helper/asset-urls';
import { truncateAddress, truncationPoints } from '@/filters';
import ScrambleMixin from '@/mixins/scramble-mixin';
import { GeneralAccount } from '@/typing/types';
import { randomHex } from '@/typing/utils';
import { assert } from '@/utils/assertions';

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
    const name =
      this.account.label.length > 0 && this.$vuetify.breakpoint.mdAndDown
        ? 'sm'
        : this.$vuetify.breakpoint.name;
    const length = truncationPoints[name] ?? 4;
    const address = truncateAddress(this.address, length);
    this.truncated = address.includes('...');
    return address;
  }

  copy(address: string) {
    navigator.clipboard.writeText(address);
  }

  get url(): string {
    const { chain, address } = this.account;
    const explorerUrl = explorerUrls[chain];
    assert(explorerUrl);
    return explorerUrl.address + address;
  }

  openLink() {
    this.$interop.openUrl(this.url);
  }
}
</script>

<style scoped lang="scss">
.labeled-address-display {
  max-height: 30px;

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

  &__actions {
    width: 61px;
    max-width: 65px;
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
