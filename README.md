# DataViewer

Simple proof of concept tool to view csv and json files, built with Streamlit.

Provides some standard data insight:
- Browse and search records.
- Find duplicate values in a column.
- Find unique values in a column.
- Get random samplings of records.
- Export any of the above records as a csv.

**Currently only handles flat json files (un-nested).**

https://simple-dataviewer.streamlit.app/

## TODO

- Json Explorer for working with nested json files. (in progress)
- Help screen.
- Caching of dataframes.
- Code refactoring to files for each piece of functionality.
- Allow selection of a column for random sampling to select different values off of.
- Find null/empty/0 values, along with a count of those values.
- Search for PII data.