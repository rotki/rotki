Avoid tracking any changes on Playground.vue
------

When using the playground to test new components and code you don't want this code to get tracked. For this you can use 
the following command to avoid accidentally committing any changes.

```bash
    git update-index --assume-unchanged src/pages/playground/index.vue   
```
If you want to make changes to the file that have to be tracked you can run the following to start tracking the changes again.

```bash
    git update-index --no-assume-unchanged frontend/app/src/pages/playground/index.vue      
```