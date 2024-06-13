import streamlit as st
import pandas as pd
from pdf2image import convert_from_path, pdfinfo_from_path
import pytesseract
import tempfile
import re
from io import StringIO
import openai
from openai import OpenAI

# Set the Tesseract command path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# OpenAI API key setup
client = OpenAI(api_key="sk-proj-akuqP2GWco082ufWChRfT3BlbkFJjgrViem1GnR0JpJLND7N")

def get_response(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content

def numbers_percentage(text):
    cleaned_text = text.replace('\n', ' ').replace('.', '').replace(',', '')
    numbers = re.findall(r'\b\d+\b', cleaned_text)
    total_words = len(cleaned_text.split())
    total_numbers = len(numbers)
    percentage_numbers = total_numbers / total_words
    return percentage_numbers

def look_variables_in_text(text, user_variables):
    base_prompt = (
        "Generate only a table with columns for Variable Name, and Value. All this information comes from a pdf uploaded. remember the format of the things asked. if you think it is a string it should be a string,if it is numeric make it numeric, if you think it is date, make it so. "
        "Start and finish the table with '|'. The desired variables are {variables}. If any variable is not found, do not retrieve it. "
        "Only create rows for the variables that are found. Verify the completeness of the extracted data to ensure the variables are captured. "
        "Look in the following text: "
    )
    prompt = base_prompt.format(variables=', '.join(user_variables)) + text
    response = get_response(prompt)
    return response

def generate_dataframe(text):
    table_text = text[text.index('|'):text.rindex('|')+1]
    df = pd.read_csv(StringIO(table_text), sep='|', skiprows=0, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.iloc[1:, 1:-1]
    return df

@st.cache_data
def find_variables(pdf_bytes, user_variables):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_bytes)
        tmp_file_path = tmp_file.name
    
    try:
        pdf_info = pdfinfo_from_path(tmp_file_path)
        total_pages = pdf_info["Pages"]
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return pd.DataFrame()

    concat_text = ''
    final_dataframe = pd.DataFrame()

    for page_number in range(1, total_pages + 1):
        try:
            image = convert_from_path(tmp_file_path, first_page=page_number, last_page=page_number)[0]
            text = pytesseract.image_to_string(image, config='--psm 6')
            concat_text += text
        except Exception as e:
            st.error(f"Error processing page {page_number}: {e}")
            continue
        
        if numbers_percentage(concat_text) > 0.1 or page_number == total_pages:
            prompt_output = look_variables_in_text(concat_text, user_variables)
            retrieved_variables = generate_dataframe(prompt_output)
            concat_text = ''

            remove_wanted = []
            for value in user_variables:
                if value in retrieved_variables['Variable Name'].values:
                    final_dataframe = pd.concat([final_dataframe, retrieved_variables[retrieved_variables['Variable Name'] == value]], ignore_index=True)
                    remove_wanted.append(value)
            user_variables = [x for x in user_variables if x not in remove_wanted]

            if len(user_variables) == 0:
                break

    return final_dataframe

# Predefined columns
predefined_columns = ['worker_id', 'worker_name', 'company_name', 'worker_start_date', 'worker_role', 'salary']

# Streamlit app

# Streamlit app
st.set_page_config(page_title="NANDU the Extractor", layout="wide")
st.title("NANDU the Extractor 🦜📄")

st.markdown("""
Welcome to **NANDU the Extractor**! This tool allows you to upload PDF files, extract employment data, and manage the data interactively.
""")

uploaded_files = st.file_uploader("Upload PDF", type="pdf", accept_multiple_files=True)

# User input for custom variables
user_input = st.text_input("Enter the desired variables separated by commas", value="worker_id, worker_name, company_name, worker_start_date, worker_role, salary")
user_variables = [var.strip() for var in user_input.split(',')]

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
