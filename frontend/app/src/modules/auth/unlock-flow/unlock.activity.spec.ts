import { describe, expect, it } from 'vitest';
import { SESSION_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { sessionCreateActivity, sessionLoginActivity } from './unlock.activity';

describe('unlock activity ids', () => {
  it('should give login and account creation their fixed ids', () => {
    expect(sessionLoginActivity.id()).toBe('session:login');
    expect(sessionCreateActivity.id()).toBe('session:create');
  });

  it('should run both on the session lane, so a login never overlaps a creation', () => {
    expect(sessionLoginActivity.laneOf?.()).toBe(SESSION_LANE);
    expect(sessionCreateActivity.laneOf?.()).toBe(SESSION_LANE);
  });
});
