import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import ListItem from '@/modules/shell/components/ListItem.vue';

describe('listItem', () => {
  let wrapper: VueWrapper<InstanceType<typeof ListItem>>;

  function createWrapper(blurContent: boolean): VueWrapper<InstanceType<typeof ListItem>> {
    return mount(ListItem, {
      props: { title: 'Ethereum', subtitle: 'ETH', blurContent },
      slots: { avatar: '<div class="avatar-content" />' },
    });
  }

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should not blur the content by default', () => {
    wrapper = createWrapper(false);
    expect(wrapper.find('.blur').exists()).toBe(false);
  });

  it('should blur only the text content when blurContent is set', () => {
    wrapper = createWrapper(true);
    expect(wrapper.find('.blur').exists()).toBe(true);
    // the avatar must remain untouched so the icon is not double-blurred
    expect(wrapper.find('.avatar .blur').exists()).toBe(false);
    expect(wrapper.find('[data-cy=list-title]').classes()).not.toContain('blur');
  });
});
