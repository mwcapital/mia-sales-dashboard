import streamlit as st
import pandas as pd
import plotly.express as px
from functions import optimize_dataframe
# At the top of your script, before creating the file uploader
# Increase file upload limit to 1GB (or your desired size)
import zipfile
import io

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        # Check if the file is a ZIP file
        if uploaded_file.name.endswith('.zip'):
 
            # Open the zip file
            with zipfile.ZipFile(io.BytesIO(uploaded_file.getvalue())) as zip_ref:
                # Get list of CSV files in the zip
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                
                if not csv_files:
                    st.error("No CSV files found in the ZIP archive.")
                    return None
                
                # Open the first CSV file in the zip
                with zip_ref.open(csv_files[0]) as csv_file:
                    # Read the CSV file
                    df = pd.read_csv(csv_file, encoding="cp1251", low_memory=False, index_col=0, sep=';', parse_dates=True)
        else:
            # Regular CSV file processing
            df = pd.read_csv(uploaded_file, encoding="cp1251", low_memory=False, index_col=0, sep=';', parse_dates=True)
        
        # Process the data
        df["product"] = df["product"].apply(eval)  # Convert to tuple
        df["продукция"] = df["product"].apply(lambda x: x[0])
        df["вид продукции"] = df["product"].apply(lambda x: x[1])
        return df
    return None

# Add file uploader to accept both CSV and ZIP files
uploaded_file = st.file_uploader("Upload your CSV file (or zipped CSV)", type=["csv", "zip"])
# Load data when file is uploaded
if uploaded_file is not None:
    df = load_data(uploaded_file)

    # Only proceed with the rest of the code if df is not None
    if df is not None:
        st.success("Data loaded successfully!")

        ################## branch selection
        if 'Branch' in df.columns:
            all_branches = ['Все компании'] + df['Branch'].unique().tolist()
            selected_branches = st.multiselect("Выберите компанию", all_branches, default='Все компании')
            if 'Все компании' not in selected_branches:
                branch_df = df[df['Branch'].isin(selected_branches)]
                branch_title = f" - {', '.join(selected_branches)} Branch"
            else:
                branch_df = df
                branch_title = " - Все компании"
        else:
            branch_df = df
            branch_title = ""

        ############## Create date components from index
        branch_df['Год'] = branch_df.index.year.astype(str)
        branch_df['Месяц'] = branch_df.index.month
        branch_df['Четверть'] = branch_df.index.quarter
        branch_df['ГодМесяц'] = branch_df.index.strftime('%Y-%m')
        branch_df['ГодЧетверть'] = branch_df['Год'].astype(str) + '-Q' + branch_df['Четверть'].astype(str)

        # Store both the filtered dataframe and the title in session state
        st.session_state['branch_df'] = branch_df
        st.session_state['branch_title'] = branch_title
        # Optional: Display a success message
        st.success(f"Данные выбранной компании сохранены в сессии")
    else:
        st.warning("There was an error processing the uploaded file. Please check the file format.")
else:
    st.info("Please upload a CSV file to proceed.")



