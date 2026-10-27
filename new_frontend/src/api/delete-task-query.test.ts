import { describe, expect, it } from 'vitest';

import { deleteTaskQuery } from '@/api/delete-task-query';

describe('delete task query', () => {
  it('omits the query string when no options are given', () => {
    expect(deleteTaskQuery()).toBe('');
    expect(deleteTaskQuery({})).toBe('');
  });

  it('sends the delete scope', () => {
    expect(deleteTaskQuery({ scope: 'single' })).toBe('?scope=single');
    expect(deleteTaskQuery({ scope: 'series' })).toBe('?scope=series');
  });

  it('encodes an optional reason', () => {
    expect(deleteTaskQuery({ scope: 'series', reason: 'delete series' })).toBe(
      '?scope=series&reason=delete%20series',
    );
  });

  it('ignores an empty reason', () => {
    expect(deleteTaskQuery({ scope: 'single', reason: '' })).toBe('?scope=single');
    expect(deleteTaskQuery({ reason: null })).toBe('');
  });
});
