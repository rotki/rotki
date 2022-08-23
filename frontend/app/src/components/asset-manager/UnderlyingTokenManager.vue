<template>
  <v-form ref="form" v-model="valid">
    <div class="text-h6">
      {{ $t('underlying_token_manager.labels.tokens') }}
    </div>
    <v-row class="mt-2">
      <v-col cols="12" md="7">
        <v-text-field
          v-model="underlyingAddress"
          :rules="addressRules"
          outlined
          :label="$t('common.address')"
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="tokenKind"
          outlined
          :label="$t('asset_form.labels.token_kind')"
          :items="evmTokenKindsData"
          item-text="label"
          item-value="identifier"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="underlyingWeight"
          type="number"
          max="100"
          min="1"
          :rules="weightRules"
          persistent-hint
          :hint="$t('underlying_token_manager.hint')"
          outlined
          :label="$t('underlying_token_manager.labels.weight')"
        >
          <template #append-outer>
            <v-btn icon :disabled="!valid" class="mt-n2" @click="addToken">
              <v-icon>mdi-plus</v-icon>
            </v-btn>
          </template>
        </v-text-field>
      </v-col>
    </v-row>
    <v-sheet outlined rounded class="underlying-tokens">
      <v-simple-table fixed-header height="200px">
        <thead>
          <tr>
            <th>{{ $t('common.address') }}</th>
            <th>{{ $t('underlying_token_manager.tokens.token_kind') }}</th>
            <th>{{ $t('underlying_token_manager.tokens.weight') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="token in value" :key="token.address">
            <td class="grow">{{ token.address }}</td>
            <td class="shrink">{{ token.tokenKind.toUpperCase() }}</td>
            <td class="shrink text-no-wrap">
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
import { EvmTokenKind } from '@rotki/common/lib/data';
import { get, set } from '@vueuse/core';
import { defineComponent, PropType, ref, toRefs } from 'vue';
import RowActions from '@/components/helper/RowActions.vue';
import i18n from '@/i18n';
import { evmTokenKindsData } from '@/services/assets/consts';
import { UnderlyingToken } from '@/services/assets/types';

export default defineComponent({
  name: 'UnderlyingTokenManager',
  components: { RowActions },
  props: {
    value: { required: true, type: Array as PropType<UnderlyingToken[]> }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { value } = toRefs(props);

    const input = (value: UnderlyingToken[]) => emit('input', value);

    const valid = ref<boolean>(false);
    const underlyingAddress = ref<string>('');
    const tokenKind = ref<EvmTokenKind>(EvmTokenKind.ERC20);
    const underlyingWeight = ref<string>('');
    const form = ref<any>(null);

    const addressRules = [
      (v: string) =>
        !!v ||
        i18n
          .t('underlying_token_manager.validation.address_non_empty')
          .toString()
    ];

    const weightRules = [
      (v: string) => {
        if (!v) {
          return i18n
            .t('underlying_token_manager.validation.non_empty')
            .toString();
        }
        const number = parseInt(v);
        if (isNaN(number)) {
          return i18n
            .t('underlying_token_manager.validation.not_valid')
            .toString();
        }

        if (number < 1 || number > 100) {
          return i18n
            .t('underlying_token_manager.validation.out_of_range')
            .toString();
        }

        return true;
      }
    ];

    const addToken = () => {
      const underlyingTokens = [...get(value)];
      const index = underlyingTokens.findIndex(
        ({ address }) => address === get(underlyingAddress)
      );

      const token = {
        address: get(underlyingAddress),
        tokenKind: get(tokenKind),
        weight: get(underlyingWeight)
      };

      if (index >= 0) {
        underlyingTokens[index] = token;
      } else {
        underlyingTokens.push(token);
      }

      (get(form) as any)?.reset();
      input(underlyingTokens);
    };

    const editToken = (token: UnderlyingToken) => {
      set(underlyingAddress, token.address);
      set(tokenKind, token.tokenKind);
      set(underlyingWeight, token.weight);
    };

    const deleteToken = (address: string) => {
      const underlyingTokens = [...get(value)];
      input(
        underlyingTokens.filter(
          ({ address: tokenAddress }) => tokenAddress !== address
        )
      );
    };

    return {
      form,
      valid,
      underlyingAddress,
      tokenKind,
      underlyingWeight,
      addressRules,
      weightRules,
      evmTokenKindsData,
      addToken,
      editToken,
      deleteToken
    };
  }
});
</script>
