<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h2>MakerDAO DSR</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12" class="loans__cards">
        <v-card>
          <v-card-title>
            Current DSR
          </v-card-title>
          <v-card-text> {{ currentDSR.dp(2) }}% </v-card-text>
        </v-card>
        <v-card>
          <v-card-title>
            Total DAI
          </v-card-title>
          <v-card-text>
            {{ totalDai.dp(floatingPrecision) }}
          </v-card-text>
        </v-card>
        <v-card v-if="premium">
          <v-card-title>
            Total DAI earned
          </v-card-title>
          <v-card-text>
            {{ totalGain.dp(floatingPrecision) }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-select
          v-model="selection"
          class="loans__account-selector"
          label="Account"
          return-object
          :items="dsrBalances"
          item-text="address"
        ></v-select>
      </v-col>
    </v-row>
    <v-row v-if="!!selection" class="loans__cards">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            DAI locked
          </v-card-title>
          <v-card-text>
            {{ selection.balance.dp(floatingPrecision) }}
          </v-card-text>
        </v-card>
        <v-card v-if="premium">
          <v-card-title>
            DAI earned
          </v-card-title>
          <v-card-text>
            {{ accountGain(selection.address).dp(floatingPrecision) }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="loans__history">
      <v-col cols="12">
        <v-card v-if="!premium">
          <v-card-title>
            History
            <v-spacer></v-spacer>
            <v-tooltip top>
              <template #activator="{ on }">
                <v-btn
                  text
                  icon
                  :href="$interop.isPackaged ? undefined : $interop.premiumURL"
                  v-on="on"
                  @click="
                    $interop.isPackaged ? $interop.upgradePremium() : undefined
                  "
                >
                  <v-icon>fa-lock</v-icon>
                </v-btn>
              </template>
              <span>
                DSR History is only supported under a premium subscription
              </span>
            </v-tooltip>
          </v-card-title>
        </v-card>
        <dsr-movement-history
          v-else
          :history="dsrHistory"
          :floating-precision="floatingPrecision"
        ></dsr-movement-history>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Vue } from 'vue-property-decorator';
import Component from 'vue-class-component';
import { createNamespacedHelpers } from 'vuex';
import BigNumber from 'bignumber.js';
import { AccountDSRMovement, DSRBalance } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';
import { DsrMovementHistory } from '@/utils/premium';

const { mapState, mapGetters: mapSessionGetters } = createNamespacedHelpers(
  'session'
);
const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    DsrMovementHistory
  },
  computed: {
    ...mapState(['premium']),
    ...mapSessionGetters(['floatingPrecision']),
    ...mapGetters([
      'currentDSR',
      'dsrBalances',
      'totalGain',
      'accountGain',
      'dsrHistory'
    ])
  }
})
export default class Loans extends Vue {
  premium!: boolean;
  floatingPrecision!: number;
  currentDSR!: BigNumber;
  dsrBalances!: DSRBalance[];
  selection: DSRBalance | null = null;
  totalGain!: BigNumber;
  accountGain!: (address: string) => BigNumber;
  dsrHistory!: AccountDSRMovement[];

  get totalDai(): BigNumber {
    return this.dsrBalances.reduce(
      (sum, { balance }) => sum.plus(balance),
      Zero
    );
  }

  async mounted() {
    await this.$store.dispatch('balances/fetchDSRBalances');
    if (this.premium) {
      await this.$store.dispatch('balances/fetchDSRHistory');
    }
  }
}
</script>

<style scoped lang="scss">
.loans {
  &__account-selector {
    padding-left: 12px;
    padding-right: 12px;
  }

  &__history {
    padding-left: 12px;
    padding-right: 12px;
  }

  &__cards {
    width: 100%;
    display: flex;
    flex-direction: row;
    align-content: space-evenly;
    ::v-deep {
      .v-card {
        margin: 12px;
        width: 100%;
        padding-bottom: 12px;
        padding-left: 12px;
        padding-right: 12px;
        .v-card__title {
          font-size: 16px;
          color: #646464;
        }
        .v-card__text {
          padding-top: 12px;
          font-weight: 500;
          font-size: 32px;
        }
      }
    }
  }
}
</style>
