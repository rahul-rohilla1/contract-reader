# Streamlit app

st.set_page_config(page_title="NANDU the Extractor", layout="wide")
st.title("NANDU the Extractor 🦜📄")

st.markdown("""
Welcome to **NANDU the Extractor**! This tool allows you to upload PDF files, extract employment data, and manage the data interactively.

### Instructions:
1. **Enter the desired columns** you want to extract, separated by commas.
2. **Upload PDF files** (you can add multiple files).
3. **View the results** extracted from the PDF files.

**Note:** Before adding more files, remove the earlier files by clicking on the 'x' next to the file name.
""")

# User input for custom variables
user_input = st.text_input("Enter the desired variables separated by commas", value="worker_id, worker_name, company_name, worker_start_date, worker_role, salary")
user_variables = [var.strip() for var in user_input.split(',')]

uploaded_files = st.file_uploader("Upload PDF", type="pdf", accept_multiple_files=True)

if 'dataframe' not in st.session_state:
    st.session_state.dataframe = pd.DataFrame()

if 'all_data' not in st.session_state:
    st.session_state.all_data = []

if 'files_processed' not in st.session_state:
    st.session_state.files_processed = set()

if uploaded_files:
    for uploaded_file in uploaded_files:
        # Read PDF file
        pdf_bytes = uploaded_file.read()

        # Extract data using find_variables function
        df = find_variables(pdf_bytes, user_variables)

        if df.empty:
            st.warning(f"No data extracted from the uploaded PDF: {uploaded_file.name}")
            continue

        # Filter the dataframe based on user-specified columns
        filtered_df = df[df['Variable Name'].isin(user_variables)].set_index('Variable Name').T
        filtered_df.reset_index(drop=True, inplace=True)

        # Append the new data to the session state dataframe
        st.session_state.all_data.append(filtered_df)
        st.session_state.dataframe = pd.concat(st.session_state.all_data, ignore_index=True)

        # Mark the file as processed
        st.session_state.files_processed.add(uploaded_file.name)

# Display the editable dataframe with increased height
if not st.session_state.dataframe.empty:
    st.write("Results:")

    # Option to select columns to display
    selected_columns = st.multiselect(
        "Select columns to display",
        options=st.session_state.dataframe.columns.tolist(),
        default=st.session_state.dataframe.columns.tolist()
    )

    # Display only the selected columns
    display_df = st.session_state.dataframe[selected_columns]

    edited_df = st.data_editor(display_df)  # Increase the height to 600 pixels

    # Update the session state with the edited dataframe (if you want to keep changes)
    st.session_state.dataframe = edited_df
    st.success("Data successfully extracted and displayed! 🎉")

st.markdown("""
---
*Made with ❤️ by Chileans and Indians*
""")
