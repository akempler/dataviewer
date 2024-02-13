import streamlit as st
import os
import pandas as pd
from pandas import json_normalize
import numpy as np
import json
from pathlib import Path
from io import StringIO
import mimetypes
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title="Data Viewer",
    layout="wide",
    # initial_sidebar_state="expanded"
)

menu = [
  'Overview',
  'Duplicates',
  'Unique',
  'Sampling'
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


  uploaded_file = st.file_uploader("Choose a file")

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

else:
  st.title("")
  st.subheader("No data to display")
  st.write("Upload a json or csv file to start viewing data.")

    