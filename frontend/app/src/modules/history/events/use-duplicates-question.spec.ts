import { describe, expect, it } from 'vitest';
import { DuplicatesAction, useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';

describe('use-duplicates-question', () => {
  const { duplicatesQuestion } = useDuplicatesQuestion();

  it('should describe what fixing one group does', () => {
    expect(duplicatesQuestion(DuplicatesAction.FIX, 1)).toEqual({
      message: 'customized_event_duplicates.actions.fix_single_confirm',
      title: 'customized_event_duplicates.actions.fix_single',
    });
  });

  it('should count the groups when fixing several', () => {
    expect(duplicatesQuestion(DuplicatesAction.FIX, 3)).toEqual({
      message: 'customized_event_duplicates.actions.fix_selected_confirm::3',
      title: 'customized_event_duplicates.actions.fix_selected',
    });
  });

  it('should word marking one or several groups as non-duplicated apart', () => {
    expect(duplicatesQuestion(DuplicatesAction.MARK_NON_DUPLICATED, 1)).toEqual({
      message: 'customized_event_duplicates.actions.mark_non_duplicated_confirm',
      title: 'customized_event_duplicates.actions.mark_non_duplicated',
    });
    expect(duplicatesQuestion(DuplicatesAction.MARK_NON_DUPLICATED, 2)).toEqual({
      message: 'customized_event_duplicates.actions.mark_non_duplicated_selected_confirm::2',
      title: 'customized_event_duplicates.actions.mark_non_duplicated_selected',
    });
  });

  it('should word restoring one or several groups apart', () => {
    expect(duplicatesQuestion(DuplicatesAction.RESTORE, 1)).toEqual({
      message: 'customized_event_duplicates.actions.restore_confirm',
      title: 'customized_event_duplicates.actions.restore',
    });
    expect(duplicatesQuestion(DuplicatesAction.RESTORE, 4)).toEqual({
      message: 'customized_event_duplicates.actions.restore_selected_confirm::4',
      title: 'customized_event_duplicates.actions.restore_selected',
    });
  });
});
