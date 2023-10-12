export class Constraints {
  static MAX_MILLISECONDS_DELAY = 2 ** 31 - 1;
  static MAX_SECONDS_DELAY = Math.floor(
    Constraints.MAX_MILLISECONDS_DELAY / 1000
  );
  static MAX_MINUTES_DELAY = Math.floor(
    Constraints.MAX_MILLISECONDS_DELAY / (1000 * 60)
  );
  static MAX_HOURS_DELAY = Math.floor(
    Constraints.MAX_MILLISECONDS_DELAY / (1000 * 60 * 60)
  );
}
