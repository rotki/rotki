import { DateFormat } from '@/types/date-format';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { computed, defineComponent, type PropType } from 'vue';

export const RuiDateTimePickerStub = defineComponent({
  template: `
      <div :data-cy="dataCy" v-bind="$attrs">
          <input
              v-model="model"
              class="input-value"
              type="text"
              :disabled="disabled">
          <div v-if="error || message" class="details">
              {{ error || message }}
          </div>
      </div>
    `,
  props: {
    modelValue: { type: Number, required: true },
    dataCy: { type: String, default: '' },
    successMessages: { type: [String, Array] as PropType<string | string[]>, default: () => [] },
    errorMessages: { type: [String, Array] as PropType<string | string[]>, default: () => [] },
    disabled: { type: Boolean, default: false },
    type: { type: String },
  },
  emits: ['update:model-value'],
  setup(props, { emit }) {
    const message = computed<string>(() => {
      const m: string | string[] = props.successMessages;
      return Array.isArray(m) ? m[0] : m;
    });

    const error = computed<string>(() => {
      const m: string | string[] = props.errorMessages;
      return Array.isArray(m) ? m[0] : m;
    });

    const model = computed({
      get() {
        return convertFromTimestamp(props.modelValue, DateFormat.DateMonthYearHourMinuteSecond, props.type === 'epoch-ms');
      },
      set(value: string) {
        const timestamp = convertToTimestamp(value, DateFormat.DateMonthYearHourMinuteSecond, props.type === 'epoch-ms');
        emit('update:model-value', timestamp);
      },
    });

    return {
      message,
      error,
      model,
    };
  },
});
