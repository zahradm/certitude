import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from typing import Any

# Expectation class definition
class Expectation:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def find_numerical_columns(self) -> list[str]:
        return self.df.select_dtypes(include=np.number).columns.tolist()

    def find_object_columns(self) -> list[str]:
        return self.df.select_dtypes(include=[np.dtype("O")]).columns.tolist()


# Initialize the Dash app with Bootstrap
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define a reusable function for creating cards
def create_card(title, content):
    return dbc.Card(
        dbc.CardBody(
            [
                html.H5(title, className="card-title"),
                content,
            ]
        ),
        className="mb-3",
    )


# App Layout
app.layout = dbc.Container(
    [
        html.H1("Data Validation Dashboard", className="my-4 text-center"),
        dbc.Row(
            [
                dbc.Col(
                    create_card(
                        "Select Data Source",
                        dcc.Dropdown(
                            id="data-input-type-dropdown",
                            options=[
                                {"label": "File", "value": "file"},
                                {"label": "Database", "value": "database"},
                            ],
                            value="file",
                            placeholder="Choose a data source...",
                        ),
                    ),
                    width=4,
                ),
                dbc.Col(html.Div(id="input-container"), width=8),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(html.Div(id="data-output-container"), width=6),
                dbc.Col(html.Div(id="columns-container"), width=6),
            ]
        ),
        html.Div(id="additional-functionality-container", className="mt-3"),
        html.Div(id="result-container", className="mt-3 text-center"),
        dcc.Store(id="stored-columns"),
    ],
    fluid=True,
)


# Callback: Update input container based on data source
@app.callback(
    Output("input-container", "children"),
    Input("data-input-type-dropdown", "value"),
)
def update_input_container(selected_value):
    if selected_value == "file":
        return create_card(
            "Upload File",
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Input(
                            id="file-path-input",
                            type="text",
                            placeholder="Enter file path...",
                            className="form-control",
                        ),
                        width=8,
                    ),
                    dbc.Col(
                        dbc.Button("Submit File", id="submit-file", color="primary", n_clicks=0),
                        width=4,
                    ),
                ],
                className="g-2",
            ),
        )
    elif selected_value == "database":
        return create_card(
            "Database Connection",
            dcc.Input(
                id="db-connection-string-input",
                type="text",
                placeholder="Enter connection string...",
                className="form-control",
            ),
        )


# Callback: Process file and display dropdown for column selection
@app.callback(
    [Output("data-output-container", "children"), Output("stored-columns", "data")],
    [Input("submit-file", "n_clicks")],
    [State("file-path-input", "value")],
)
def process_file(n_clicks, file_path):
    if n_clicks > 0 and file_path:
        try:
            df = pd.read_csv(file_path)
            expectation = Expectation(df)
            numerical_columns = expectation.find_numerical_columns()
            non_numerical_columns = expectation.find_object_columns()

            return create_card(
                "File Loaded Successfully",
                dcc.Dropdown(
                    id="column-type-dropdown",
                    options=[
                        {"label": "Numerical Columns", "value": "numerical"},
                        {"label": "Non-Numerical Columns", "value": "non_numerical"},
                    ],
                    placeholder="Select column type...",
                ),
            ), {
                "numerical": numerical_columns,
                "non_numerical": non_numerical_columns,
                "file_path": file_path,
            }
        except Exception as e:
            return create_card("Error", f"Failed to read file: {e}"), {}
    return create_card("Error", "Please provide a valid file path."), {}


# Callback: Update columns and additional functionality
@app.callback(
    [Output("columns-container", "children"), Output("additional-functionality-container", "children")],
    Input("column-type-dropdown", "value"),
    State("stored-columns", "data"),
)
def update_columns_and_functionality(selected_type, stored_columns):
    if selected_type and stored_columns:
        columns = stored_columns.get(selected_type)
        if not columns:
            return create_card("Error", f"No {selected_type} columns found."), ""

        column_selection = create_card(
            "Select a Column",
            dcc.Dropdown(
                id="column-selection-dropdown",
                options=[{"label": col, "value": col} for col in columns],
                placeholder=f"Select a {selected_type.replace('_', ' ')} column...",
            ),
        )

        if selected_type == "numerical":
            functionality = create_card(
                "Statistical Operations",
                dcc.Dropdown(
                    id="numerical-operation-dropdown",
                    options=[
                        {"label": "Mean", "value": "mean"},
                        {"label": "Median", "value": "median"},
                        {"label": "Standard Deviation", "value": "std"},
                    ],
                    placeholder="Choose an operation...",
                ),
            )
        else:
            functionality = create_card(
                "Categorical Operations",
                dcc.Dropdown(
                    id="non-numerical-operation-dropdown",
                    options=[
                        {"label": "Mode", "value": "mode"},
                        {"label": "Count Unique Values", "value": "unique"},
                    ],
                    placeholder="Choose an operation...",
                ),
            )
        return column_selection, functionality
    return "", ""


# Callback: Display results
@app.callback(
    Output("result-container", "children"),
    [
        Input("column-selection-dropdown", "value"),
        Input("numerical-operation-dropdown", "value"),
        Input("non-numerical-operation-dropdown", "value"),
    ],
    State("stored-columns", "data"),
)
def display_result(selected_column, numerical_operation, non_numerical_operation, stored_columns):
    if not stored_columns or "file_path" not in stored_columns:
        return "Error: File path not available."

    file_path = stored_columns["file_path"]
    try:
        df = pd.read_csv(file_path)
        if not selected_column:
            return "Please select a column."

        if numerical_operation:
            operations = {
                "mean": df[selected_column].mean,
                "median": df[selected_column].median,
                "std": df[selected_column].std,
            }
            return f"The {numerical_operation} of {selected_column} is {operations[numerical_operation]():.2f}."
        elif non_numerical_operation:
            operations = {
                "mode": lambda: df[selected_column].mode()[0],
                "unique": lambda: df[selected_column].nunique(),
            }
            return f"The {non_numerical_operation} of {selected_column} is {operations[non_numerical_operation]()}."
    except Exception as e:
        return f"Error: {e}"

    return "Please select a valid operation."


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
