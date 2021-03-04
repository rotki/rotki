<template>
  <v-form ref="form" v-model="valid">
    <div class="text-h6">
      {{ $t('underlying_token_manager.labels.tokens') }}
    </div>
    <v-row class="mt-2">
      <v-col>
        <v-text-field
          v-model="underlyingAddress"
          :rules="addressRules"
          outlined
          :label="$t('underlying_token_manager.labels.address')"
        />
      </v-col>
      <v-col>
        <v-text-field
          v-model="underlyingWeight"
          type="number"
          max="100"
          min="1"
          :rules="rules"
          outlined
          :label="$t('underlying_token_manager.labels.weight')"
        />
      </v-col>
      <v-col cols="auto">
        <v-btn icon class="mt-3" :disabled="!valid" @click="addToken">
          <v-icon>mdi-plus</v-icon>
        </v-btn>
      </v-col>
    </v-row>
    <v-sheet outlined rounded class="underlying-tokens">
      <v-simple-table>
        <thead>
          <tr>
            <th>{{ $t('underlying_token_manager.tokens.address') }}</th>
            <th>{{ $t('underlying_token_manager.tokens.weight') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="token in value" :key="token.address">
            <td class="grow">{{ token.address }}</td>
            <td class="shrink">
              {{
                $t('underlying_token_manager.tokens.weight_percentage', {
                  weight: token.weight
                })
              }}
            </td>
            <td>
              <row-actions
                :edit-tooltip="$t('underlying_token_manager.edit_tooltip')"
                :delete-tooltip="$t('underlying_token_manager.delete_tooltip')"
                @delete-click="deleteToken(token.address)"
                @edit-click="editToken(token)"
              />
            </td>
          </tr>
        </tbody>
      </v-simple-table>
    </v-sheet>
  </v-form>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';
import RowActions from '@/components/helper/RowActions.vue';
import { UnderlyingToken } from '@/services/assets/types';

@Component({
  components: { Fragment, RowActions }
})
export default class UnderlyingTokenManager extends Vue {
  @Prop({ required: true, type: Array })
  value!: UnderlyingToken[];
  @Emit()
  input(_value: UnderlyingToken[]) {}

  valid: boolean = false;

  underlyingAddress: string = '';
  underlyingWeight: string = '';

  readonly addressRules = [
    (v: string) =>
      !!v ||
      this.$t(
        'underlying_token_manager.validation.address_non_empty'
      ).toString()
  ];

  readonly rules = [
    (v: string) => {
      if (!v) {
        return this.$t(
          'underlying_token_manager.validation.non_empty'
        ).toString();
      }
      const number = parseInt(v);
      if (isNaN(number)) {
        return this.$t(
          'underlying_token_manager.validation.not_valid'
        ).toString();
      }

      if (number < 1 || number > 100) {
        return this.$t(
          'underlying_token_manager.validation.out_of_range'
        ).toString();
      }

      return true;
    }
  ];

  addToken() {
    const underlyingTokens = [...this.value];
    const index = underlyingTokens.findIndex(
      ({ address }) => address === this.underlyingAddress
    );

    const token = {
      address: this.underlyingAddress,
      weight: this.underlyingWeight
    };

    if (index >= 0) {
      underlyingTokens[index] = token;
    } else {
      underlyingTokens.push(token);
    }

    (this.$refs.form as any).reset();
    this.input(underlyingTokens);
  }

  editToken(token: UnderlyingToken) {
    this.underlyingAddress = token.address;
    this.underlyingWeight = token.weight;
  }

  deleteToken(address: string) {
    const underlyingTokens = [...this.value];
    this.input(
      underlyingTokens.filter(
        ({ address: tokenAddress }) => tokenAddress !== address
      )
    );
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.underlying-tokens {
  height: 200px;

  td {
    &:first-child {
      width: 100%;
    }
  }

  @extend .themed-scrollbar;
}
</style>
