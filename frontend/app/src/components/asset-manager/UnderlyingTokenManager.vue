<script setup lang="ts">
import { EvmTokenKind, type UnderlyingToken } from '@rotki/common/lib/data';
import useVuelidate from '@vuelidate/core';
import { between, helpers, numeric, required } from '@vuelidate/validators';
import { type PropType } from 'vue';
import { evmTokenKindsData } from '@/types/blockchain/chains';

const props = defineProps({
  value: { required: true, type: Array as PropType<UnderlyingToken[]> }
});

const emit = defineEmits<{ (e: 'input', value: UnderlyingToken[]): void }>();
const { tc } = useI18n();

const { value } = toRefs(props);

const input = (value: UnderlyingToken[]) => emit('input', value);

const underlyingAddress = ref<string>('');
const tokenKind = ref<EvmTokenKind>(EvmTokenKind.ERC20);
const underlyingWeight = ref<string>('');
const form = ref<any>(null);

const rules = {
  address: {
    required: helpers.withMessage(
      tc('underlying_token_manager.validation.address_non_empty'),
      required
    )
  },
  weight: {
    required: helpers.withMessage(
      tc('underlying_token_manager.validation.non_empty'),
      required
    ),
    notNaN: helpers.withMessage(
      tc('underlying_token_manager.validation.not_valid'),
      numeric
    ),
    minMax: helpers.withMessage(
      tc('underlying_token_manager.validation.out_of_range'),
      between(1, 100)
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    address: underlyingAddress,
    weight: underlyingWeight
  },
  { $autoDirty: true, $stopPropagation: true }
);

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
  get(v$).$reset();
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
</script>

<template>
  <v-form ref="form" :value="!v$.$invalid">
    <div class="text-h6">
      {{ tc('underlying_token_manager.labels.tokens') }}
    </div>
    <v-row class="mt-2">
      <v-col cols="12" md="7">
        <v-text-field
          v-model="underlyingAddress"
          :error-messages="v$.address.$errors.map(e => e.$message)"
          outlined
          :label="tc('common.address')"
        />
      </v-col>
      <v-col cols="12" md="2">
        <v-select
          v-model="tokenKind"
          outlined
          :label="tc('asset_form.labels.token_kind')"
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
          :error-messages="v$.weight.$errors.map(e => e.$message)"
          persistent-hint
          :hint="tc('underlying_token_manager.hint')"
          outlined
          :label="tc('underlying_token_manager.labels.weight')"
        >
          <template #append-outer>
            <v-btn icon :disabled="v$.$invalid" class="mt-n2" @click="addToken">
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
            <th>{{ tc('common.address') }}</th>
            <th>{{ tc('underlying_token_manager.tokens.token_kind') }}</th>
            <th>{{ tc('underlying_token_manager.tokens.weight') }}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="token in value" :key="token.address">
            <td class="grow">{{ token.address }}</td>
            <td class="shrink">{{ token.tokenKind.toUpperCase() }}</td>
            <td class="shrink text-no-wrap">
              {{
                tc('underlying_token_manager.tokens.weight_percentage', 0, {
                  weight: token.weight
                })
              }}
            </td>
            <td>
              <row-actions
                :edit-tooltip="tc('underlying_token_manager.edit_tooltip')"
                :delete-tooltip="tc('underlying_token_manager.delete_tooltip')"
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
