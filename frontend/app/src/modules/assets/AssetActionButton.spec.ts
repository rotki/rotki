import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AssetActionButton from './AssetActionButton.vue';

interface ActionProps {
  icon?: string;
  color?: 'primary' | 'warning' | 'error';
  tooltip?: string;
  dataCy?: string;
}

function mountButton(props: ActionProps = {}): VueWrapper<InstanceType<typeof AssetActionButton>> {
  return mount(AssetActionButton, {
    props: {
      color: 'primary',
      icon: 'lu-dollar-sign',
      tooltip: 'Update price',
      ...props,
    },
  });
}

describe('modules/assets/AssetActionButton', () => {
  it('should emit click when the button is pressed', async () => {
    const wrapper = mountButton();

    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('click')).toHaveLength(1);
  });

  it('should apply the data-cy hook to the button itself, not the tooltip root', () => {
    const wrapper = mountButton({ dataCy: 'asset-update-price' });

    expect(wrapper.find('button').attributes('data-cy')).toBe('asset-update-price');
  });

  it('should omit the data-cy attribute when no hook is given', () => {
    const wrapper = mountButton();

    expect(wrapper.find('button').attributes('data-cy')).toBeUndefined();
  });
});
