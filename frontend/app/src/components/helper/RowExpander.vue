<template>
  <span>
    <v-btn icon small @click="click">
      <v-icon v-if="expanded" small>
        mdi-chevron-up
      </v-icon>
      <v-icon v-else small>
        mdi-chevron-down
      </v-icon>
    </v-btn>
  </span>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class RowExpander extends Vue {
  @Prop({ required: true, type: Boolean })
  expanded!: boolean;

  @Emit()
  click() {}
}
</script>
