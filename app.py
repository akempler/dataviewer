import streamlit as st
import os
import pandas as pd
from pandas import json_normalize
import numpy as np
import json
from pathlib import Path
from io import StringIO
import io
import mimetypes
from streamlit_option_menu import option_menu
import random

st.set_page_config(
    page_title="Data Viewer",
    layout="wide",
    # initial_sidebar_state="expanded"
)

menu = [
  'Overview',
  'Duplicates',
  'Unique',
  'Sampling',
  'Data Dictionary'
]

with st.sidebar:
  
  st.sidebar.markdown(
    """
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
    <style>
      .st-emotion-cache-16txtl3 h1.sidebar_title {
        font-size: 2.5rem;
        font-weight: 600;
      }
      .material-symbols-outlined {
        font-family: 'Material Symbols Outlined', sans-serif;
        font-size: 1.75rem;
        font-weight: 400;
        margin-right: 4px;
      }
    </style>
    """,
    unsafe_allow_html=True,
  )

  heading = '<h1 class="sidebar_title"><span class="material-symbols-outlined">data_table</span>Data Viewer</h1>'
  st.sidebar.markdown(heading, unsafe_allow_html=True)


  uploaded_file = st.file_uploader("Upload a file:", type=["csv", "json"])

  if uploaded_file is not None:
    
    if uploaded_file.name.endswith('.json'):
      # dataframe = pd.read_json(uploaded_file)
      # Avoid using read_json as it does not handle nested json well.
      json_file = json.load(uploaded_file)
      dataframe = json_normalize(json_file)
    elif uploaded_file.name.endswith('.csv'):
      dataframe = pd.read_csv(uploaded_file)
    else:
      st.write("File type not supported")


  page = option_menu(
    "Data Insights", 
    menu, 
    default_index=menu.index("Overview"), 
    orientation="vertical"
  )


if "dataframe" in locals():
  if page == "Overview":
    st.subheader("Data Overview")

    st.write("Record count: ", dataframe.shape[0])

    # Only show the tabs if it is a json file.
    if "json_file" in locals():
      tab1, tab2 = st.tabs(["Data Table", "Raw Json"])
      with tab1:
        st.write("Column count: ", dataframe.shape[1])
        st.write(dataframe)

      with tab2:
        st.json(json_file, expanded=False)
    else:
      st.write("Column count: ", dataframe.shape[1])
      st.write(dataframe)

  if page == "Duplicates":
    with st.form("duplicate"):
      st.subheader("Duplicate Values Finder")
      # Show a sampling of the data.
      sampling = dataframe.sample(3)
      st.write("Random sample of data:")
      st.write(sampling)

      option = st.selectbox('Select a column to find duplicate values on.', dataframe.columns)

      submitted = st.form_submit_button("Find")

      if submitted:
        duplicateRows = dataframe[dataframe.duplicated(subset=option, keep=False)]
        num_rows = len(duplicateRows)
        st.write("Record count: ", num_rows)
        st.write("Duplicate data:")
        duplicateRows = duplicateRows.sort_values(by=option)
        st.write(duplicateRows)

  if page == "Unique":
    with st.form("unique"):
      st.subheader("Unique Values Finder")
      # Show a sampling of the data.
      sampling = dataframe.sample(3)
      st.write("Random sample of data:")
      st.write(sampling)
      
      option = st.selectbox('Select a column to find unique values on.', dataframe.columns)

      submitted = st.form_submit_button("Find")

      if submitted:
        uniqueRows = dataframe[option].unique()
        num_rows = len(uniqueRows)
        st.write("Record count: ", num_rows)
        st.write("Unique data:")
        st.write(uniqueRows)

        counts = dataframe[option].value_counts()
        st.write("Value counts:")
        st.write(counts)

  if page == "Sampling":
    with st.form("sampling"):
      st.subheader("Data Sampler")
      # Show a sampling of the data.
      sampling_number = st.number_input('Number of records to sample', min_value=1, max_value=500, value=5)

      submitted = st.form_submit_button("Create Sample Data")

      if submitted:
        sampling = dataframe.sample(sampling_number)
        st.write(sampling)

  if page == "Data Dictionary":
    st.subheader("Create a Data Dictionary")
    # Create a sampling of the data to use as example data for the dictionary.
    st.write("Create an example data dictionary for the data.")
    st.write("Download the dictionary as a csv file by hovering over the table header and clicking the download icon.")
    st.write("You can then upload the file to Google Docs.")

    


    cols_list = dataframe.columns.tolist()


    with st.form("sampling_method"):

      help = '''
      By default, the samplings will be just random samplings of data in the column. 
      Select the columns you want to use unique sampling for. 
      This is appropriate for columns that have a limited number of unique values such as taxonomies.
      '''
      st.write(help)

      sampling_options = st.multiselect(
        'Which columns should use unique sampling?',
        cols_list,
        placeholder="Select columns")

      sampling_submitted = st.form_submit_button("Create Data Dictionary")

    if sampling_submitted:

      sampleset = {}
      # Loop through cols_list and create a sample of the data for each column:
      for col in cols_list:
          # check if the column is in the sampling_options list
          if col in sampling_options:
            # add the unique values to the sampleset
            unique = dataframe[col].unique()
            count = len(unique)
            if count >= 1 and count < 3:
              sample_list = random.sample(list(unique), count)
            else:
              sample_list = random.sample(list(unique), 3)

            # create a dataframe from the sample_list
            sampleset[col] = pd.DataFrame(sample_list, columns=[col])
          else:
            # add a random sample of the data to the sampleset
            sampleset[col] = dataframe[col].sample(3)

      dict_dataframe = pd.DataFrame(columns=['Field Name', 'Data Type', 'Description', 'Sample Data'])

      for col in cols_list:
        samples = sampleset[col].values
        try:
          samples_string = ' | \n\n'.join(samples)
        except:
          samples = samples.flatten()
          samples_string = ' | \n\n'.join(samples)
        
        new_row = {'Field Name': col, 'Data Type': [''], 'Description': [''], 'Sample Data': [samples_string]}
        new_row_dataframe = pd.DataFrame.from_dict(new_row)
        dict_dataframe = pd.concat([dict_dataframe, new_row_dataframe], ignore_index=True)

      st.write(dict_dataframe)

      # Create a new filename for the data dictionary.
      newfilename = uploaded_file.name.split('.')[0] + '_dd'
      newfilename = newfilename.replace(" ", "_")
      newfilename = newfilename.lower()
      # add the date to the filename
      newfilename = newfilename + '_' + pd.to_datetime('today').strftime('%Y%m%d') + '.xlsx'

      # buffer to use for excel writer
      buffer = io.BytesIO()

      with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        
      # Create a dataframe with the filename and current date:
        info_dataframe = pd.DataFrame({'Filename': [uploaded_file.name], 'Date': [pd.to_datetime('today').strftime('%Y-%m-%d')]})
        info_dataframe.to_excel(writer, sheet_name='Sheet1', index=False)
        dict_dataframe.to_excel(writer, sheet_name='Sheet1', startrow=4, index=False)
        writer.close()
        exportbtn = st.download_button(
            label="Download data as Excel",
            data=buffer,
            file_name=newfilename,
            mime='application/vnd.ms-excel'
      )

else:
  # Default welcome screen.
  st.header("A simple csv / json data viewer")
  st.write("a useful tool for reviewing source data for Drupal and other CMS migrations and integrations.")

  container = st.container(border=True)
  container.subheader("No data to display")
  container.info("Use the file upload form to get started.")

    