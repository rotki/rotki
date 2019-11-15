import dotenv from 'dotenv';

// eslint-disable-next-line no-undef
jasmine.getEnv().addReporter({
  specStarted: result => (window.currentTest = result),
  specDone: result => (window.currentTest = result)
});

dotenv.config({ path: './.env.test' });
