import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { getActionEntry } from '@/modules/settings/settings-actions';
import { getRegistryEntry } from '@/modules/settings/settings-registry';

describe('settingsItem', () => {
  it('should derive its dom id from the registry anchor of setting-key', () => {
    const anchor = getRegistryEntry('autoDetectTokens')?.anchor;
    const wrapper = mount(SettingsItem, {
      props: { settingKey: 'autoDetectTokens' },
      slots: { title: 'Auto detect tokens' },
    });
    expect(anchor).toBeDefined();
    expect(wrapper.get('div').attributes('id')).toBe(anchor);
  });

  it('should render the setting title from the registry when no title slot is given', () => {
    const titleKey = getRegistryEntry('autoDetectTokens')?.search?.titleKey;
    const wrapper = mount(SettingsItem, {
      props: { settingKey: 'autoDetectTokens' },
    });
    expect(titleKey).toBeDefined();
    // the i18n stub echoes the key, so the derived title is the titleKey itself
    expect(wrapper.text()).toContain(titleKey);
  });

  it('should derive its dom id from the action anchor of action-key', () => {
    const anchor = getActionEntry('purgeData')?.anchor;
    const wrapper = mount(SettingsItem, {
      props: { actionKey: 'purgeData' },
      slots: { title: 'Purge data' },
    });
    expect(anchor).toBeDefined();
    expect(wrapper.get('div').attributes('id')).toBe(anchor);
  });

  it('should render the action title from the registry when no title slot is given', () => {
    const titleKey = getActionEntry('purgeData')?.titleKey;
    const wrapper = mount(SettingsItem, {
      props: { actionKey: 'purgeData' },
    });
    expect(titleKey).toBeDefined();
    expect(wrapper.text()).toContain(titleKey);
  });

  it('should let a title slot override the registry title', () => {
    const wrapper = mount(SettingsItem, {
      props: { settingKey: 'autoDetectTokens' },
      slots: { title: 'Custom title' },
    });
    expect(wrapper.text()).toContain('Custom title');
    expect(wrapper.text()).not.toContain('auto_detect_tokens');
  });

  it('should let an explicit id win over the setting-key anchor', () => {
    const wrapper = mount(SettingsItem, {
      attrs: { id: 'setting-explicit' },
      props: { settingKey: 'autoDetectTokens' },
      slots: { title: 'Auto detect tokens' },
    });
    expect(wrapper.get('div').attributes('id')).toBe('setting-explicit');
  });

  it('should render no id when neither setting-key nor id is given', () => {
    const wrapper = mount(SettingsItem, {
      slots: { title: 'Plain' },
    });
    expect(wrapper.get('div').attributes('id')).toBeUndefined();
  });
});
