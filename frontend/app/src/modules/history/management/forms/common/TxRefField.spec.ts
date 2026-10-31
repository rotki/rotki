import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import TxRefField from '@/modules/history/management/forms/common/TxRefField.vue';

type Props = InstanceType<typeof TxRefField>['$props'];

function createWrapper(props: Partial<Props> = {}): VueWrapper<InstanceType<typeof TxRefField>> {
  return mount(TxRefField, {
    props: { errorMessages: [], label: 'Tx Hash', modelValue: '', ...props },
  });
}

describe('txRefField', () => {
  it('should emit what the user types', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=tx-ref] input').setValue('0xabc');

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['0xabc']);
  });

  it('should show the error messages it is given', () => {
    const wrapper = createWrapper({ errorMessages: ['not a hash'] });

    expect(wrapper.find('[data-testid=tx-ref]').text()).toContain('not a hash');
  });

  it('should show neither a spinner nor a retry while no lookup runs', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=tx-ref-loading]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=tx-ref-retry]').exists()).toBe(false);
  });

  it('should show a spinner while the lookup runs', () => {
    const wrapper = createWrapper({ canRetry: true, loading: true });

    expect(wrapper.find('[data-testid=tx-ref-loading]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=tx-ref-retry]').exists()).toBe(false);
  });

  it('should offer a retry once the lookup failed', async () => {
    const wrapper = createWrapper({ canRetry: true });

    await wrapper.find('[data-testid=tx-ref-retry]').trigger('click');

    expect(wrapper.emitted('retry')).toHaveLength(1);
  });

  it('should lock the field when asked to', () => {
    const wrapper = createWrapper({ disabled: true });

    expect(wrapper.find<HTMLInputElement>('[data-testid=tx-ref] input').element.disabled).toBe(true);
  });
});
