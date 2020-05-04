<template>
  <v-card :loading="isLoading" class="pb-3">
    <v-row no-gutters class="pa-3 rotkibeige primary--text">
      <v-toolbar-title class="font-weight-medium">
        {{ name }} balances
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <span>
        <v-tooltip v-if="canRefresh" bottom>
          <template #activator="{ on }">
            <v-btn
              icon
              x-small
              color="primary"
              class="summary-card__refresh-icon"
              @click="refresh(name)"
              v-on="on"
            >
              <v-icon color="primary">
                fa-refresh
              </v-icon>
            </v-btn>
          </template>
          Refresh {{ name }} balances
        </v-tooltip>
      </span>
    </v-row>
    <v-list>
      <slot></slot>
    </v-list>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class SummaryCard extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: false })
  icon?: string;
  @Prop({ required: false, default: false })
  isLoading!: boolean;
  @Prop({ required: false, default: false, type: Boolean })
  canRefresh!: boolean;

  refresh(balanceSource: string) {
    this.$emit('refresh', balanceSource.toLowerCase());
  }
}
</script>

<style scoped lang="scss">
.summary-card__refresh-icon {
  filter: grayscale(100%);

  &:hover {
    filter: grayscale(0);
  }
}
</style>
