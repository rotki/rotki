describe('awaitParallelExecution', () => {
  test('instant resolve if no items exist', async () => {
    await expect(
      awaitParallelExecution<{ id: string }>(
        [],
        id => id,
        () => Promise.resolve()
      )
    ).resolves.toBeUndefined();
  });

  test('resolves after all promises resolve', async () => {
    const items = 10;
    const p1 = vi.fn();
    await expect(
      awaitParallelExecution<{ id: string }>(
        Array.from({ length: items }, (_, i) => ({
          id: i + 1
        })),
        id => id,
        item => p1(item.id)
      )
    ).resolves.toBeUndefined();
    expect(p1).toHaveBeenCalledTimes(10);
  });
});
