<template>
  <div v-if="!group" class="font-weight-medium">
    {{ $t('account_balances.data_table.group.standalone') }}
  </div>
  <div v-else>
    <span class="font-weight-medium">
      {{ $t('account_balances.data_table.group.xpub') }}
    </span>
    <span :style="privacyStyle">
      {{ group }}
    </span>
    <v-btn small icon @click="deleteClicked">
      <v-icon small>mdi-delete-outline</v-icon>
    </v-btn>
  </div>
</template>
<script lang="ts">
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import PrivacyMixin from '@/mixins/privacy-mixin';

@Component({})
export default class AccountGroupHeader extends Mixins(PrivacyMixin) {
  @Prop({ required: true, type: String })
  group!: string;

  @Emit()
  deleteClicked() {}
}
</script>
