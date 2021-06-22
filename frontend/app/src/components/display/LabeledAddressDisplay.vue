<template>
  <div class="d-flex flex-row labeled-address-display align-center">
    <v-tooltip top open-delay="400" :disabled="!truncated">
      <template #activator="{ on }">
        <span
          class="labeled-address-display__address"
          :class="
            $vuetify.breakpoint.xsOnly
              ? 'labeled-address-display__address--mobile'
              : null
          "
          v-on="on"
        >
          <v-chip label outlined class="labeled-address-display__chip">
            <span v-if="!!label" class="text-truncate">
              {{
                $t('labeled_address_display.label', {
                  label: label
                })
              }}
            </span>
            <span
              v-if="!!label && displayAddress && !$vuetify.breakpoint.smAndDown"
              class="px-1"
            >
              {{ $t('labeled_address_display.divider') }}
            </span>
            <span
              v-if="!$vuetify.breakpoint.smAndDown || !label"
              :class="privacyMode ? 'blur-content' : null"
            >
              {{ displayAddress }}
            </span>
          </v-chip>
        </span>
      </template>
      <span v-if="!!label"> {{ account.label }} <br /> </span>
      <span> {{ address }} </span>
    </v-tooltip>
    <div class="labeled-address-display__actions">
      <hash-link :text="account.address" buttons small :chain="account.chain" />
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

  get breakpoint(): string {
    return this.account.label.length > 0 && this.$vuetify.breakpoint.mdAndDown
      ? 'sm'
      : this.$vuetify.breakpoint.name;
  }

  get truncationLength(): number {
    let truncationPoint = truncationPoints[this.breakpoint];
    if (truncationPoint && this.account.label) {
      return 4;
    }
    return truncationPoint ?? 4;
  }

  get displayAddress(): string {
    const address = truncateAddress(this.address, this.truncationLength);
    if (address.length >= this.address.length) {
      this.truncated = false;
      return this.address;
    }
    this.truncated = address.includes('...');
    return address;
  }

  get label(): string {
    const bp = this.$vuetify.breakpoint;
    const label = this.account.label;
    let length = -1;

    if (bp.xlOnly && label.length > 50) {
      length = 47;
    } else if (bp.lgOnly && label.length > 38) {
      length = 35;
    } else if (bp.md && label.length > 27) {
      length = 24;
    } else if (bp.smOnly && label.length > 19) {
      length = 16;
    }

    if (length > 0) {
      return label.substr(0, length) + '...';
    }

    return label;
  }

  copy(address: string) {
    navigator.clipboard.writeText(address);
  }
}
</script>

<style scoped lang="scss">
.labeled-address-display {
  max-height: 30px;
  width: 100%;

  &__address {
    width: 100%;
    font-weight: 500;
    padding-top: 6px;
    padding-bottom: 6px;

    &--mobile {
      max-width: 120px;
    }

    ::v-deep {
      .v-chip {
        background-color: white !important;

        &--label {
          border-top-right-radius: 0 !important;
          border-bottom-right-radius: 0 !important;
        }
      }
    }
  }

  &__actions {
    height: 32px;
    width: 70px;
    max-width: 75px;
    background-color: var(--v-rotki-light-grey-base);
    border: 1px solid rgba(0, 0, 0, 0.12);
    border-left-width: 0;
    border-radius: 0 4px 4px 0;
    display: inline-block;
  }

  &__chip {
    width: 100%;
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
