import flet as ft
import json
import io
import random
from pathlib import Path

import pandas as pd
from pandas import json_normalize

MAX_DATATABLE_ROWS = 200
MENU = ["Overview", "Duplicates", "Unique", "Empty", "Sampling", "Data Dictionary"]


def df_to_datatable(df: pd.DataFrame, max_rows: int = MAX_DATATABLE_ROWS) -> tuple[ft.DataTable, int]:
    """Convert pandas DataFrame to Flet DataTable. Returns (DataTable, total_rows)."""
    total_rows = len(df)
    display_df = df.head(max_rows)

    columns = [
        ft.DataColumn(label=ft.Text(str(col), overflow=ft.TextOverflow.ELLIPSIS))
        for col in display_df.columns
    ]
    rows = []
    for _, row in display_df.iterrows():
        cells = [
            ft.DataCell(ft.Text(str(val) if pd.notna(val) else "", overflow=ft.TextOverflow.ELLIPSIS))
            for val in row
        ]
        rows.append(ft.DataRow(cells=cells))

    table = ft.DataTable(
        columns=columns,
        rows=rows,
        expand=True,
        border=ft.Border.all(1),
    )
    return table, total_rows


def load_file(file_path: str, filename: str) -> tuple[pd.DataFrame, dict | None]:
    """Load file from path. Returns (dataframe, json_file or None)."""
    ext = Path(filename).suffix.lower()
    if ext == ".json":
        with open(file_path, encoding="utf-8") as f:
            json_file = json.load(f)
        df = json_normalize(json_file)
        return df, json_file
    if ext == ".csv":
        df = pd.read_csv(file_path)
        return df, None
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
        return df, None
    raise ValueError("File type not supported")


def main(page: ft.Page):
    page.title = "Data Viewer"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    # App state
    state = {"dataframe": None, "json_file": None, "filename": None}

    # Refs for dynamic updates
    main_content = ft.Ref[ft.Container]()
    nav_rail = ft.Ref[ft.NavigationRail]()

    # In Flet 0.80+, FilePicker is a Service and must be registered on page.services.
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def show_page(idx: int):
        df = state["dataframe"]
        json_file = state.get("json_file")
        content = main_content.current
        if content is None:
            return

        if df is None:
            content.content = ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                controls=[
                    ft.Text("A simple csv / json / Excel data viewer", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.Text("A useful tool for reviewing source data for Drupal and other CMS migrations and integrations."),
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("No data to display", style=ft.TextThemeStyle.HEADLINE_SMALL),
                                ft.Row(
                                    controls=[
                                        ft.Icon(ft.Icons.INFO_OUTLINE),
                                        ft.Text("Use the file upload button in the sidebar to get started."),
                                    ],
                                    spacing=8,
                                ),
                            ],
                            spacing=8,
                        ),
                        border=ft.Border.all(1),
                        border_radius=8,
                        padding=16,
                    ),
                ],
                spacing=16,
                alignment=ft.MainAxisAlignment.START,
            )
        else:
            page_name = MENU[idx]
            if page_name == "Overview":
                content.content = build_overview(df, json_file)
            elif page_name == "Duplicates":
                content.content = build_duplicates(df)
            elif page_name == "Unique":
                content.content = build_unique(df)
            elif page_name == "Empty":
                content.content = build_empty(df)
            elif page_name == "Sampling":
                content.content = build_sampling(df)
            elif page_name == "Data Dictionary":
                content.content = build_data_dictionary(df, state["filename"], file_picker)
        page.update()

    def on_nav_change(e):
        idx = e.control.selected_index
        if idx is not None:
            show_page(idx)

    async def on_upload_click(e):
        files = await file_picker.pick_files(
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv", "json", "xlsx", "xls"],
        )
        if not files:
            return
        f = files[0]
        path = f.path
        if not path:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("File path not available. Run as a desktop app (flet run) for file uploads."),
                open=True,
            )
            page.update()
            return
        if not Path(path).exists():
            page.snack_bar = ft.SnackBar(content=ft.Text("File not found or no longer accessible."), open=True)
            page.update()
            return
        try:
            df, json_file = load_file(path, f.name)
            state["dataframe"] = df
            state["json_file"] = json_file
            state["filename"] = f.name
            nav_rail.current.selected_index = 0
            nav_rail.current.visible = True
            show_page(0)
        except Exception as ex:
            page.snack_bar = ft.SnackBar(content=ft.Text(str(ex)), open=True)
        page.update()

    # Sidebar - expand=False ensures it keeps its width and doesn't get compressed
    sidebar = ft.Container(
        width=220,
        expand=False,
        padding=12,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.TABLE_CHART, size=28),
                        ft.Text("Data Viewer", style=ft.TextThemeStyle.HEADLINE_SMALL),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Button(
                    "Upload a file",
                    icon=ft.Icons.UPLOAD_FILE,
                    on_click=on_upload_click,
                    expand=True,
                ),
                ft.Divider(height=1),
                ft.NavigationRail(
                    ref=nav_rail,
                    selected_index=0,
                    label_type=ft.NavigationRailLabelType.ALL,
                    min_width=80,
                    min_extended_width=180,
                    extended=True,
                    visible=False,
                    on_change=on_nav_change,
                    destinations=[
                        ft.NavigationRailDestination(icon=ft.Icons.TABLE_CHART, label="Overview"),
                        ft.NavigationRailDestination(icon=ft.Icons.FILTER_LIST, label="Duplicates"),
                        ft.NavigationRailDestination(icon=ft.Icons.FILTER_1, label="Unique"),
                        ft.NavigationRailDestination(icon=ft.Icons.INBOX, label="Empty"),
                        ft.NavigationRailDestination(icon=ft.Icons.SHUFFLE, label="Sampling"),
                        ft.NavigationRailDestination(icon=ft.Icons.MENU_BOOK, label="Data Dictionary"),
                    ],
                ),
            ],
            tight=True,
            spacing=12,
            alignment=ft.MainAxisAlignment.START,
        ),
    )

    # Main content area
    main_area = ft.Container(
        ref=main_content,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[
                ft.Text("A simple csv / json / Excel data viewer", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                ft.Text("A useful tool for reviewing source data for Drupal and other CMS migrations and integrations."),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("No data to display", style=ft.TextThemeStyle.HEADLINE_SMALL),
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.INFO_OUTLINE),
                                    ft.Text("Use the file upload button in the sidebar to get started."),
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=8,
                    ),
                    border=ft.Border.all(1),
                    border_radius=8,
                    padding=16,
                ),
            ],
            spacing=16,
            alignment=ft.MainAxisAlignment.START,
        ),
        expand=True,
        padding=16,
    )

    layout = ft.Row(
        controls=[sidebar, ft.VerticalDivider(width=1), main_area],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    page.add(layout)


def build_overview(df: pd.DataFrame, json_file: dict | None) -> ft.Control:
    table, total_rows = df_to_datatable(df)
    header = ft.Column(
        controls=[
            ft.Text("Data Overview", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Text(f"Record count: {total_rows}"),
            ft.Text(f"Column count: {df.shape[1]}"),
        ],
        spacing=4,
    )

    if json_file is not None:
        tabs = ft.Tabs(
            expand=True,
            tabs=[
                ft.Tab(
                    text="Data Table",
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(f"Showing first {min(len(df), MAX_DATATABLE_ROWS)} of {total_rows} rows"),
                                ft.Container(content=table, expand=True),
                            ],
                            expand=True,
                        ),
                    ),
                ),
                ft.Tab(
                    text="Raw Json",
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text(
                                    json.dumps(json_file, indent=2),
                                    selectable=True,
                                    overflow=ft.TextOverflow.CLIP,
                                ),
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                    ),
                ),
            ],
        )
        return ft.Column(controls=[header, tabs], expand=True, scroll=ft.ScrollMode.AUTO)
    else:
        return ft.Column(
            controls=[
                header,
                ft.Text(f"Showing first {min(len(df), MAX_DATATABLE_ROWS)} of {total_rows} rows"),
                ft.Container(content=table, expand=True),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )


def build_duplicates(df: pd.DataFrame) -> ft.Control:
    col_dropdown = ft.Dropdown(
        label="Select a column to find duplicate values on",
        options=[ft.dropdown.Option(key=col, text=col) for col in df.columns],
    )
    result_area = ft.Ref[ft.Column]()

    sampling_table, _ = df_to_datatable(df.sample(min(3, len(df))))

    def on_find(e):
        col = col_dropdown.value
        if not col:
            return
        duplicate_rows = df[df.duplicated(subset=[col], keep=False)]
        duplicate_rows = duplicate_rows.sort_values(by=col)
        dup_table, num = df_to_datatable(duplicate_rows)
        area = result_area.current
        if area:
            area.controls = [
                ft.Text(f"Record count: {num}"),
                ft.Text("Duplicate data:"),
                ft.Container(content=dup_table, expand=True),
            ]
            area.update()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        controls=[
            ft.Text("Duplicate Values Finder", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Text("Random sample of data:"),
            ft.Container(content=sampling_table),
            col_dropdown,
            ft.Button("Find", on_click=on_find),
            ft.Container(content=ft.Column(ref=result_area, controls=[])),
        ],
        spacing=12,
    )


def build_unique(df: pd.DataFrame) -> ft.Control:
    col_dropdown = ft.Dropdown(
        label="Select a column to find unique values on",
        options=[ft.dropdown.Option(key=col, text=col) for col in df.columns],
    )
    result_area = ft.Ref[ft.Column]()

    sampling_table, _ = df_to_datatable(df.sample(min(3, len(df))))

    def on_find(e):
        col = col_dropdown.value
        if not col:
            return
        unique_vals = df[col].unique()
        counts = df[col].value_counts()
        count_df = counts.reset_index()
        count_df.columns = ["Value", "Count"]
        count_table, _ = df_to_datatable(count_df, max_rows=500)
        area = result_area.current
        if area:
            area.controls = [
                ft.Text(f"Record count: {len(unique_vals)}"),
                ft.Text("Value counts:"),
                ft.Container(content=count_table),
            ]
            area.update()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        controls=[
            ft.Text("Unique Values Finder", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Text("Random sample of data:"),
            ft.Container(content=sampling_table),
            col_dropdown,
            ft.Button("Find", on_click=on_find),
            ft.Container(content=ft.Column(ref=result_area, controls=[])),
        ],
        spacing=12,
    )


def build_empty(df: pd.DataFrame) -> ft.Control:
    col_dropdown = ft.Dropdown(
        label="Select a column to find empty values on",
        options=[ft.dropdown.Option(key=col, text=col) for col in df.columns],
    )
    result_area = ft.Ref[ft.Column]()

    sampling_table, _ = df_to_datatable(df.sample(min(3, len(df))))

    def on_find(e):
        col = col_dropdown.value
        if not col:
            return
        empty_cells = df[(df[col] == "") | (df[col].isnull()) | (df[col] == " ")]
        num_cells = len(empty_cells)
        area = result_area.current
        if area:
            area.controls = [
                ft.Text(f"Record count: {df.shape[0]}"),
                ft.Text(f"Number of empty records: {num_cells}"),
            ]
            area.update()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        controls=[
            ft.Text("Empty Values Finder", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Text("Random sample of data:"),
            ft.Container(content=sampling_table),
            col_dropdown,
            ft.Button("Find", on_click=on_find),
            ft.Container(content=ft.Column(ref=result_area, controls=[])),
        ],
        spacing=12,
    )


def build_sampling(df: pd.DataFrame) -> ft.Control:
    num_input = ft.TextField(
        label="Number of records to sample",
        value="5",
        input_filter=ft.NumbersOnlyInputFilter(),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    result_area = ft.Ref[ft.Column]()

    def on_sample(e):
        try:
            n = int(num_input.value or 5)
            n = max(1, min(500, n))
        except ValueError:
            n = 5
        sample_df = df.sample(min(n, len(df)))
        sample_table, _ = df_to_datatable(sample_df)
        area = result_area.current
        if area:
            area.controls = [ft.Container(content=sample_table)]
            area.update()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        controls=[
            ft.Text("Data Sampler", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            num_input,
            ft.Button("Create Sample Data", on_click=on_sample),
            ft.Container(content=ft.Column(ref=result_area, controls=[])),
        ],
        spacing=12,
    )


def build_data_dictionary(
    df: pd.DataFrame, filename: str | None, file_picker: ft.FilePicker
) -> ft.Control:
    cols_list = df.columns.tolist()
    sampling_table, _ = df_to_datatable(df.sample(min(3, len(df))))

    help_text = (
        "By default, the samplings will be just random samplings of data in the column. "
        "Select the columns you want to use unique sampling for. "
        "This is appropriate for columns that have a limited number of unique values such as taxonomies."
    )

    # Checkboxes for each column
    checkbox_refs: dict[str, ft.Ref[ft.Checkbox]] = {col: ft.Ref[ft.Checkbox]() for col in cols_list}
    checkbox_list = ft.Column(
        controls=[
            ft.Checkbox(ref=checkbox_refs[col], label=col, value=False)
            for col in cols_list
        ],
        scroll=ft.ScrollMode.AUTO,
    )

    dict_result_area = ft.Ref[ft.Column]()

    def on_create_dict(e):
        sampling_options = []
        for col in cols_list:
            ref = checkbox_refs[col].current
            if ref is not None and ref.value:
                sampling_options.append(col)

        sampleset = {}
        for col in cols_list:
            if col in sampling_options:
                unique = df[col].unique()
                count = len(unique)
                if count == 0:
                    sampleset[col] = df[col].sample(min(3, len(df)))
                elif count < 3:
                    sampleset[col] = pd.DataFrame(list(unique), columns=[col])
                else:
                    sample_list = random.sample(list(unique), 3)
                    sampleset[col] = pd.DataFrame(sample_list, columns=[col])
            else:
                sampleset[col] = df[col].sample(min(3, len(df)))

        dict_dataframe = pd.DataFrame(columns=[
            "Field Name", "Data Type", "Null", "Default Value", "Description", "Sample Data", "Questions"
        ])
        for col in cols_list:
            samples = sampleset[col].values.flatten()
            str_samples = [str(x) for x in samples]
            samples_string = " | \n".join(str_samples)
            new_row_df = pd.DataFrame([{
                "Field Name": col,
                "Data Type": "",
                "Null": "",
                "Default Value": "",
                "Description": "",
                "Sample Data": samples_string,
                "Questions": "",
            }])
            dict_dataframe = pd.concat([dict_dataframe, new_row_df], ignore_index=True)

        dict_table, _ = df_to_datatable(dict_dataframe, max_rows=500)

        newfilename = (filename or "data").split(".")[0] + "_dd"
        newfilename = newfilename.replace(" ", "_").lower()
        newfilename = newfilename + "_" + pd.to_datetime("today").strftime("%Y%m%d") + ".xlsx"

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            info_df = pd.DataFrame({"Info": [filename or "data"]})
            info_df.to_excel(writer, sheet_name="Sheet1", index=False)
            dict_dataframe.to_excel(writer, sheet_name="Sheet1", startrow=4, index=False)
        excel_bytes = buffer.getvalue()

        def make_save_handler(data: bytes, fname: str):
            async def handler(ev):
                path = await file_picker.save_file(
                    file_name=fname,
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["xlsx"],
                    src_bytes=data,
                )
                if path:
                    with open(path, "wb") as f:
                        f.write(data)

            return handler

        area = dict_result_area.current
        if area:
            area.controls = [
                ft.Container(content=dict_table),
                ft.Button(
                    "Download data as Excel",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=make_save_handler(excel_bytes, newfilename),
                ),
            ]
            area.update()

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        controls=[
            ft.Text("Create a Data Dictionary", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            ft.Text("Create an example data dictionary for the data."),
            ft.Text("Download the dictionary as a csv file by exporting from the table, or use the Excel download button below."),
            ft.Text("Random sample of data:"),
            ft.Container(content=sampling_table),
            ft.Text(help_text),
            ft.Text("Which columns should use unique sampling?"),
            ft.Container(content=checkbox_list, height=150),
            ft.Button("Create Data Dictionary", on_click=on_create_dict),
            ft.Container(content=ft.Column(ref=dict_result_area, controls=[])),
        ],
        spacing=12,
    )


if __name__ == "__main__":
    ft.run(main)
