<template>
  <table-expand-container visible :colspan="cols" :padded="false">
    <template #title>
      {{ tc('asset_table.underlying_tokens') }}
    </template>
    <v-simple-table>
      <thead>
        <tr>
          <th>{{ tc('common.address') }}</th>
          <th>{{ tc('underlying_token_manager.tokens.token_kind') }}</th>
          <th>{{ tc('underlying_token_manager.tokens.weight') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="token in asset.underlyingTokens" :key="token.address">
          <td class="grow">
            <hash-link :text="token.address" full-address />
          </td>
          <td class="shrink">{{ token.tokenKind.toUpperCase() }}</td>
          <td class="shrink">
            {{
              tc('underlying_token_manager.tokens.weight_percentage', 0, {
                weight: token.weight
              })
            }}
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </table-expand-container>
</template>

<script setup lang="ts">
import { SupportedAsset } from '@rotki/common/lib/data';
import { PropType } from 'vue';

defineProps({
  cols: {
    required: true,
    type: Number
  },
  asset: {
    required: true,
    type: Object as PropType<SupportedAsset>
  }
});

const { tc } = useI18n();
</script>
