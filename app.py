import re
import streamlit as st
import pandas as pd
from pandas import json_normalize
import json
from pathlib import Path
import io
import random

from streamlit_option_menu import option_menu

import database as db

st.set_page_config(
    page_title="Data Viewer",
    layout="wide",
)

# Initialize session state
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "selected_file_path" not in st.session_state:
    st.session_state.selected_file_path = None
if "dataframe" not in st.session_state:
    st.session_state.dataframe = None
if "json_file" not in st.session_state:
    st.session_state.json_file = None
if "current_filename" not in st.session_state:
    st.session_state.current_filename = None
if "project_created_success" not in st.session_state:
    st.session_state.project_created_success = None

menu = [
    "Overview",
    "Duplicates",
    "Unique",
    "Empty",
    "Sampling",
    "Data Dictionary",
]


def load_file_from_path(file_path: str) -> tuple[pd.DataFrame, dict | None]:
    """Load dataframe and optional json_file from filesystem path."""
    path = Path(file_path)
    if not path.exists():
        return None, None

    if path.suffix.lower() == ".json":
        with open(path) as f:
            json_data = json.load(f)
        df = json_normalize(json_data)
        return df, json_data
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        return df, None
    elif path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
        return df, None
    return None, None


def load_file_from_upload(uploaded_file) -> tuple[pd.DataFrame, dict | None]:
    """Load dataframe and optional json_file from Streamlit UploadedFile."""
    if uploaded_file.name.endswith(".json"):
        json_data = json.load(uploaded_file)
        df = json_normalize(json_data)
        return df, json_data
    elif uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        return df, None
    elif uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        return df, None
    return None, None


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

    # Success message after project creation (persists after rerun, expander collapsed)
    if st.session_state.project_created_success:
        st.success(f"Project '{st.session_state.project_created_success}' created.")

    # Project picker
    db.init_db()
    projects = db.list_projects()
    project_options = ["-- Select a project --"] + [p[1] for p in projects]
    project_id_map = {p[1]: p[0] for p in projects}

    project_default_idx = 0
    if st.session_state.current_project_id is not None:
        for i, p in enumerate(projects):
            if p[0] == st.session_state.current_project_id:
                project_default_idx = i + 1
                break

    selected_project_name = st.selectbox(
        "Project",
        project_options,
        index=project_default_idx,
        key="project_picker",
    )

    prev_project_id = st.session_state.current_project_id
    if selected_project_name != "-- Select a project --":
        new_project_id = project_id_map[selected_project_name]
        st.session_state.current_project_id = new_project_id
        if prev_project_id != new_project_id:
            st.session_state.selected_file_path = None
            st.session_state.dataframe = None
            st.session_state.json_file = None
            st.session_state.current_filename = None
    else:
        st.session_state.current_project_id = None
        st.session_state.selected_file_path = None
        st.session_state.dataframe = None
        st.session_state.json_file = None
        st.session_state.current_filename = None

    # New project button (collapsed after creation so success message is visible)
    # Use a counter for the form key so the field is empty after each successful create
    if "new_project_form_key" not in st.session_state:
        st.session_state.new_project_form_key = 0
    with st.expander("Create new project", expanded=False):
        new_project_name = st.text_input(
            "Project name", key=f"new_project_name_{st.session_state.new_project_form_key}"
        )
        if st.button("Create project"):
            if new_project_name and new_project_name.strip():
                try:
                    project_name = new_project_name.strip()
                    new_project_id = db.create_project(project_name)
                    st.session_state.current_project_id = new_project_id
                    st.session_state.project_created_success = project_name
                    st.session_state.new_project_form_key += 1
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
            else:
                st.warning("Enter a project name.")

    # Clear success message after it has been displayed
    if st.session_state.project_created_success:
        st.session_state.project_created_success = None

    # Delete project (only when project selected)
    if st.session_state.current_project_id is not None:
        with st.expander("Delete project", expanded=False):
            st.warning(
                "This will permanently delete the project and all its uploaded files."
            )
            if st.button("Delete project", type="secondary"):
                try:
                    project_name = selected_project_name
                    db.delete_project(st.session_state.current_project_id)
                    st.session_state.current_project_id = None
                    st.session_state.selected_file_path = None
                    st.session_state.dataframe = None
                    st.session_state.json_file = None
                    st.session_state.current_filename = None
                    st.success(f"Project '{project_name}' deleted.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    # Data source section (only when project selected)
    if st.session_state.current_project_id is not None:
        project_files = db.list_files(st.session_state.current_project_id)

        # Existing files selector
        if project_files:
            file_options = ["-- Select existing file --"] + [f[1] for f in project_files]
            file_id_map = {f[1]: (f[0], f[2]) for f in project_files}

            file_default_idx = 0
            if st.session_state.current_filename:
                for i, f in enumerate(project_files):
                    if f[1] == st.session_state.current_filename:
                        file_default_idx = i + 1
                        break

            selected_file_name = st.selectbox(
                "Existing files",
                file_options,
                index=file_default_idx,
                key="existing_file_picker",
            )

            if selected_file_name != "-- Select existing file --":
                file_id, file_path = file_id_map[selected_file_name]
                abs_path = db.get_file_path(file_id)
                if abs_path:
                    df, jf = load_file_from_path(abs_path)
                    if df is not None:
                        st.session_state.dataframe = df
                        st.session_state.json_file = jf
                        st.session_state.selected_file_path = abs_path
                        st.session_state.current_filename = selected_file_name

        # Upload new file - key includes project_id so switching projects clears the
        # uploader and prevents the same file from being saved to multiple projects
        uploaded_file = st.file_uploader(
            "Upload a file:",
            type=["csv", "json", "xlsx"],
            key=f"file_uploader_{st.session_state.current_project_id}",
        )

        if uploaded_file is not None:
            # Only process each upload once - Streamlit reruns keep the file in memory,
            # which would otherwise trigger add_file on every rerun and create duplicates.
            upload_signature = (
                uploaded_file.name,
                uploaded_file.size,
                st.session_state.current_project_id,
            )
            if st.session_state.get("last_processed_upload") == upload_signature:
                pass  # Already processed this upload, skip to avoid duplicates
            else:
                df, jf = load_file_from_upload(uploaded_file)
                if df is not None:
                    # Save to project and load
                    try:
                        uploaded_file.seek(0)
                        data = uploaded_file.getvalue()
                        db.add_file(
                            st.session_state.current_project_id,
                            uploaded_file.name,
                            data,
                        )
                        st.session_state.last_processed_upload = upload_signature
                        st.session_state.dataframe = df
                        st.session_state.json_file = jf
                        st.session_state.current_filename = uploaded_file.name
                        # Resolve path for selected file (newly added)
                        project_files = db.list_files(
                            st.session_state.current_project_id
                        )
                        for fid, fname, fpath in project_files:
                            if fname == uploaded_file.name:
                                st.session_state.selected_file_path = db.get_file_path(
                                    fid
                                )
                                break
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save file: {e}")
                else:
                    st.write("File type not supported")
        else:
            # Clear processed-upload tracking when user clears the file picker
            st.session_state.pop("last_processed_upload", None)
    else:
        st.info("Create or select a project to get started.")

    page = option_menu(
        "Data Insights",
        menu,
        default_index=menu.index("Overview"),
        orientation="vertical",
    )


# Main content
dataframe = st.session_state.dataframe
json_file = st.session_state.json_file
current_filename = st.session_state.current_filename

if dataframe is not None:
    if page == "Overview":
        st.subheader("Data Overview")

        st.write("Record count: ", dataframe.shape[0])

        # Search panel
        params = st.session_state.get("overview_search_params")
        with st.container(border=False):
            st.markdown("**Search:**")
            with st.form("overview_search"):
                col_options = ["-- Select a column --"] + list(dataframe.columns)
                col_default_idx = (
                    col_options.index(params["col"])
                    if params and params["col"] in col_options
                    else 0
                )
                col_sel = st.selectbox(
                    "Search in column:",
                    col_options,
                    index=col_default_idx,
                    key="overview_search_col",
                )
                search_val = st.text_input(
                    "Search for",
                    value=params["val"] if params else "",
                    placeholder="e.g. 15-1254.00 OR 5-1251.00",
                    key="overview_search_val",
                )
                st.caption("Separate multiple terms with OR to match any of them.")
                match_mode = st.radio(
                    "Match:",
                    ["Contains", "Exact"],
                    horizontal=True,
                    index=1 if params and params.get("mode") == "Exact" else 0,
                    key="overview_match_mode",
                )
                submitted = st.form_submit_button("Search")

            if submitted:
                if search_val and col_sel != "-- Select a column --":
                    st.session_state.overview_search_params = {
                        "col": col_sel,
                        "val": search_val,
                        "mode": match_mode,
                    }
                else:
                    st.session_state.overview_search_params = None

        # Apply filter if search was submitted with valid params
        display_df = dataframe
        params = st.session_state.get("overview_search_params")
        if params and params["val"] and len(dataframe) > 0:
            terms = [
                t.strip()
                for t in re.split(r"\s+or\s+", params["val"], flags=re.IGNORECASE)
                if t.strip()
            ]
            if terms:
                col_str = dataframe[params["col"]].astype(str)
                if params["mode"] == "Contains":
                    mask = col_str.str.contains(
                        terms[0], case=False, na=False, regex=False
                    )
                    for term in terms[1:]:
                        mask = mask | col_str.str.contains(
                            term, case=False, na=False, regex=False
                        )
                else:
                    mask = col_str == terms[0]
                    for term in terms[1:]:
                        mask = mask | (col_str == term)
                display_df = dataframe[mask]
            st.write("Filtered: ", len(display_df), " records")

        if json_file is not None:
            tab1, tab2 = st.tabs(["Data Table", "Raw Json"])
            with tab1:
                st.write("Column count: ", dataframe.shape[1])
                st.write(display_df)

            with tab2:
                st.json(json_file, expanded=False)
        else:
            st.write("Column count: ", dataframe.shape[1])
            st.write(display_df)

    if page == "Duplicates":
        with st.form("duplicate"):
            st.subheader("Duplicate Values Finder")
            sample_size = min(3, len(dataframe))
            sampling = dataframe.sample(sample_size) if sample_size > 0 else dataframe
            st.write("Random sample of data:")
            st.write(sampling)

            option = st.selectbox(
                "Select a column to find duplicate values on.", dataframe.columns
            )

            submitted = st.form_submit_button("Find")

            if submitted:
                duplicateRows = dataframe[
                    dataframe.duplicated(subset=option, keep=False)
                ]
                num_rows = len(duplicateRows)
                st.write("Record count: ", num_rows)
                st.write("Duplicate data:")
                duplicateRows = duplicateRows.sort_values(by=option)
                st.write(duplicateRows)

    if page == "Unique":
        with st.form("unique"):
            st.subheader("Unique Values Finder")
            sample_size = min(3, len(dataframe))
            sampling = dataframe.sample(sample_size) if sample_size > 0 else dataframe
            st.write("Random sample of data:")
            st.write(sampling)

            option = st.selectbox(
                "Select a column to find unique values on.", dataframe.columns
            )

            submitted = st.form_submit_button("Find")

            if submitted:
                uniqueRows = dataframe[option].unique()
                num_rows = len(uniqueRows)
                st.write("Record count: ", num_rows)

                counts = dataframe[option].value_counts()
                st.write("Value counts:")
                st.write(counts)

    if page == "Empty":
        with st.form("empty"):
            st.subheader("Empty Values Finder")
            sample_size = min(3, len(dataframe))
            sampling = dataframe.sample(sample_size) if sample_size > 0 else dataframe
            st.write("Random sample of data:")
            st.write(sampling)

            option = st.selectbox(
                "Select a column to find empty values on.", dataframe.columns
            )

            submitted = st.form_submit_button("Find")

            if submitted:
                empty_cells = dataframe[
                    (dataframe[option] == "")
                    | (dataframe[option].isnull())
                    | (dataframe[option] == " ")
                ]

                num_cells = len(empty_cells)
                st.write("Record count: ", dataframe.shape[0])
                st.write("Number of empty records: ", num_cells)

    if page == "Sampling":
        with st.form("sampling"):
            st.subheader("Data Sampler")
            sampling_number = st.number_input(
                "Number of records to sample",
                min_value=1,
                max_value=min(500, len(dataframe)) if len(dataframe) > 0 else 1,
                value=min(5, len(dataframe)) if len(dataframe) > 0 else 1,
            )
            random_sampling = st.checkbox(
                "Random Sampling",
                value=True,
                help="When checked, sample random rows. When unchecked, use the first N rows.",
            )

            submitted = st.form_submit_button("Create Sample Data")

            if submitted:
                if random_sampling:
                    sampling = dataframe.sample(sampling_number)
                else:
                    sampling = dataframe.head(sampling_number)
                st.write(sampling)

    if page == "Data Dictionary":
        st.subheader("Create a Data Dictionary")
        st.write("Create an example data dictionary for the data.")
        st.write(
            "Download the dictionary as a csv file by hovering over the table header and clicking the download icon."
        )
        st.write("You can then upload the file to Google Docs.")
        st.write("Alternatively you can download the dictionary as an Excel file.")

        sample_size = min(3, len(dataframe))
        sampling = dataframe.sample(sample_size) if sample_size > 0 else dataframe
        st.write("Random sample of data:")
        st.write(sampling)

        cols_list = dataframe.columns.tolist()

        with st.form("sampling_method"):
            help_text = """
      By default, the samplings will be just random samplings of data in the column.
      Select the columns you want to use unique sampling for.
      This is appropriate for columns that have a limited number of unique values such as taxonomies.
      """
            st.write(help_text)

            sampling_options = st.multiselect(
                "Which columns should use unique sampling?",
                cols_list,
                placeholder="Select columns",
            )

            sampling_submitted = st.form_submit_button("Create Data Dictionary")

        if sampling_submitted:
            sampleset = {}
            for col in cols_list:
                if col in sampling_options:
                    unique = dataframe[col].unique()
                    count = len(unique)
                    if count >= 1 and count < 3:
                        sample_list = random.sample(list(unique), count)
                    else:
                        sample_list = random.sample(list(unique), 3)
                    sampleset[col] = pd.DataFrame(sample_list, columns=[col])
                else:
                    sample_size = min(3, len(dataframe))
                    sampleset[col] = dataframe[col].sample(sample_size)

            dict_dataframe = pd.DataFrame(
                columns=[
                    "Field Name",
                    "Data Type",
                    "Null",
                    "Default Value",
                    "Description",
                    "Sample Data",
                    "Questions",
                ]
            )

            for col in cols_list:
                samples = sampleset[col].values
                try:
                    samples_string = " | \n".join(samples)
                except Exception:
                    samples = samples.flatten()
                    str_samples = [str(x) for x in samples]
                    samples_string = " | \n".join(str_samples)

                new_row = {
                    "Field Name": col,
                    "Data Type": [""],
                    "Null": [""],
                    "Default Value": [""],
                    "Description": [""],
                    "Sample Data": [samples_string],
                    "Questions": [""],
                }
                new_row_dataframe = pd.DataFrame.from_dict(new_row)
                dict_dataframe = pd.concat(
                    [dict_dataframe, new_row_dataframe], ignore_index=True
                )

            st.write(dict_dataframe)

            base_name = (
                Path(current_filename or "data").stem
                .replace(" ", "_")
                .lower()
            )
            newfilename = f"{base_name}_dd_{pd.to_datetime('today').strftime('%Y%m%d')}.xlsx"

            buffer = io.BytesIO()

            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                info_dataframe = pd.DataFrame(
                    {"Info": [current_filename or "data"]}
                )
                info_dataframe.to_excel(writer, sheet_name="Sheet1", index=False)
                dict_dataframe.to_excel(
                    writer, sheet_name="Sheet1", startrow=4, index=False
                )
                exportbtn = st.download_button(
                    label="Download data as Excel",
                    data=buffer,
                    file_name=newfilename,
                    mime="application/vnd.ms-excel",
                )

else:
    st.header("A simple csv / json / Excel data viewer")
    st.write(
        "a useful tool for reviewing source data for Drupal and other CMS migrations and integrations."
    )

    container = st.container(border=True)
    container.subheader("No data to display")
    container.info(
        "Select a project, then choose an existing file or upload a new one to get started."
    )
