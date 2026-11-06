import { describe, expect, it } from 'vitest';
import { useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';

describe('use-duplicates-question', () => {
  const { fixQuestion, markNonDuplicatedQuestion, restoreQuestion } = useDuplicatesQuestion();

  it('should describe what fixing one group does', () => {
    expect(fixQuestion(1)).toEqual({
      confirmLabel: 'customized_event_duplicates.actions.fix',
      message: 'customized_event_duplicates.actions.fix_single_confirm',
      title: 'customized_event_duplicates.actions.fix_single',
    });
  });

  it('should count the groups when fixing several', () => {
    expect(fixQuestion(3)).toEqual({
      confirmLabel: 'customized_event_duplicates.actions.fix',
      message: 'customized_event_duplicates.actions.fix_selected_confirm::3',
      title: 'customized_event_duplicates.actions.fix_selected',
    });
  });

  it('should word marking one or several groups as non-duplicated apart', () => {
    expect(markNonDuplicatedQuestion(1)).toEqual({
      confirmLabel: 'customized_event_duplicates.actions.mark_non_duplicated',
      message: 'customized_event_duplicates.actions.mark_non_duplicated_confirm',
      title: 'customized_event_duplicates.actions.mark_non_duplicated',
    });
    expect(markNonDuplicatedQuestion(2)).toEqual({
      confirmLabel: 'customized_event_duplicates.actions.mark_non_duplicated',
      message: 'customized_event_duplicates.actions.mark_non_duplicated_selected_confirm::2',
      title: 'customized_event_duplicates.actions.mark_non_duplicated_selected',
    });
  });

  it('should word restoring one or several groups apart', () => {
    expect(restoreQuestion(1)).toEqual({
      confirmLabel: 'customized_event_duplicates.actions.restore',
      message: 'customized_event_duplicates.actions.restore_confirm',
      title: 'customized_event_duplicates.actions.restore',
    });
    expect(restoreQuestion(4)).toEqual({
      confirmLabel: 'customized_event_duplicates.actions.restore',
      message: 'customized_event_duplicates.actions.restore_selected_confirm::4',
      title: 'customized_event_duplicates.actions.restore_selected',
    });
  });
});
