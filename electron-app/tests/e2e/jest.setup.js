import dotenv from 'dotenv';

jasmine.getEnv().addReporter({
  specStarted: result => (window.currentTest = result),
  specDone: result => (window.currentTest = result)
});

dotenv.config({ path: './.env.test' });
