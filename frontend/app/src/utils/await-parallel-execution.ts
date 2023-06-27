/**
 * Awaits for a limited parallelization queue to complete processing all queued items.
 *
 * @template T The type of the items used in the queue
 * @param items The items that will be passed to the fn.
 * @param genId Generates an identifier from an item.
 * @param fn Takes an item <T> and returns a void {@link Promise}. The function represents queued work.
 * @param parallelization The number of operations to run in parallel
 */
export const awaitParallelExecution = async <T>(
  items: T[],
  genId: (item: T) => string,
  fn: (item: T) => Promise<void>,
  parallelization = 4
): Promise<void> => {
  const queue = new LimitedParallelizationQueue(parallelization);
  return new Promise(resolve => {
    if (items.length === 0) {
      return resolve();
    }
    queue.setOnCompletion(() => {
      queue.setOnCompletion(undefined);
      resolve();
    });
    for (const item of items) {
      queue.queue(genId(item), () => fn(item));
    }
  });
};
