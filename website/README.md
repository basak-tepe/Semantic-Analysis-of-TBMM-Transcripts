
  # Turkish Parliament Info Website

  This is a code bundle for Turkish Parliament Info Website. The original project is available at https://www.figma.com/design/csqyNL5kA1taJKJ9RyeIqQ/Turkish-Parliament-Info-Website.

  ## Data

  The website uses real MP data from `mp_lookup.csv`. The CSV is converted to JSON format for use in the application.

  ### Updating MP Data

  If you update `mp_lookup.csv`, regenerate the JSON file by running:
  ```bash
  node scripts/convertCSV.js
  ```

  This will update `src/data/mpData.json` with the latest data from the CSV.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.
  