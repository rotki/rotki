<template>
  <span>
    <v-tooltip top>
      <template #activator="{ on, attrs }">
        <v-btn
          small
          v-bind="attrs"
          icon
          class="mx-1"
          v-on="on"
          @click="editClick"
        >
          <v-icon :disabled="disabled" small>
            mdi-pencil-outline
          </v-icon>
        </v-btn>
      </template>
      <span>{{ editTooltip }}</span>
    </v-tooltip>
    <v-tooltip top>
      <template #activator="{ on, attrs }">
        <v-btn
          small
          v-bind="attrs"
          icon
          class="mx-1"
          v-on="on"
          @click="deleteClick"
        >
          <v-icon :disabled="disabled" small>
            mdi-delete-outline
          </v-icon>
        </v-btn>
      </template>
      <span>{{ deleteTooltip }}</span>
    </v-tooltip>
  </span>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class RowActions extends Vue {
  @Prop({ required: false, type: Boolean })
  disabled!: boolean;
  @Prop({ required: true, type: String })
  editTooltip!: string;
  @Prop({ required: true, type: String })
  deleteTooltip!: string;

  @Emit()
  editClick() {}

  @Emit()
  deleteClick() {}
}
</script>
