import { DebugStateGroup } from '@shared/ipc';
import { beforeEach, describe, expect, it } from 'vitest';
import { resetDebugState } from '@/modules/shell/app/debug-state-reset';

describe('modules/shell/app/debug-state-reset', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('should remove the first-run keys from both storages', () => {
    localStorage.setItem('rotki.last_version', '1.44.0');
    localStorage.setItem('rotki_skip_asset_db_version', '30');
    localStorage.setItem('rotki.asset_update_check.day', '2026-08-14');
    sessionStorage.setItem('rotki.messages.welcome', '{}');
    sessionStorage.setItem('skip_update', '1');

    const removed = resetDebugState(DebugStateGroup.FIRST_RUN);

    expect(removed).toHaveLength(5);
    expect(localStorage.getItem('rotki.last_version')).toBeNull();
    expect(localStorage.getItem('rotki_skip_asset_db_version')).toBeNull();
    expect(localStorage.getItem('rotki.asset_update_check.day')).toBeNull();
    expect(sessionStorage.getItem('rotki.messages.welcome')).toBeNull();
    expect(sessionStorage.getItem('skip_update')).toBeNull();
  });

  it('should remove user-scoped keys matched by suffix', () => {
    localStorage.setItem('user-id-1.rotki_query_status', '{}');
    localStorage.setItem('user-id-2.rotki_query_status', '{}');

    const removed = resetDebugState(DebugStateGroup.FIRST_RUN);

    expect(removed).toEqual(expect.arrayContaining(['user-id-1.rotki_query_status', 'user-id-2.rotki_query_status']));
    expect(localStorage).toHaveLength(0);
  });

  it('should remove user-scoped keys matched by prefix', () => {
    sessionStorage.setItem('rotki.migrated_addresses.abc123', '[]');
    sessionStorage.setItem('rotki.migrated_addresses.def456', '[]');

    const removed = resetDebugState(DebugStateGroup.FIRST_RUN);

    expect(removed).toEqual(expect.arrayContaining([
      'rotki.migrated_addresses.abc123',
      'rotki.migrated_addresses.def456',
    ]));
    expect(sessionStorage).toHaveLength(0);
  });

  it('should keep the backend url, login memory and preferences', () => {
    const preserved = {
      'rotki.animations_enabled': 'true',
      'rotki.backend_url': 'http://localhost:4242',
      'rotki.backend_url_session': 'true',
      'rotki.remember_username': 'true',
      'rotki.selected_theme': 'dark',
      'rotki.table_sorting': '{}',
      'rotki.username': 'testuser',
    };
    Object.entries(preserved).forEach(([key, value]) => localStorage.setItem(key, value));

    const removed = resetDebugState(DebugStateGroup.FIRST_RUN);

    expect(removed).toEqual([]);
    Object.entries(preserved).forEach(([key, value]) => {
      expect(localStorage.getItem(key)).toBe(value);
    });
  });
});
