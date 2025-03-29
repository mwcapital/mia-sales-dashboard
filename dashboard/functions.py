import pandas as pd
from dateutil.parser import parse
from fuzzywuzzy import fuzz
import re
import streamlit as st

def header_finder(df):

    for index, row in df.iterrows():
        # Count the number of non nan values in a row
        non_nan_count = df.iloc[index, 1:].notna().sum()  # Check columns 1 to end
        if non_nan_count >= 6:  # Adjust threshold as needed
            header_row = index
            break


    if header_row is not None:
        # Step 2: Define the range to check (three rows above and below)
        start_row = max(0, header_row - 1)  # Avoid going below index 0
        end_row =  header_row + 1

        # Step 3: Check surrounding rows for "Ссылка"
        additional_header_row = None
        for i in range(start_row, end_row + 1):
            if i != header_row:  # Skip the header_row itself
                # Convert the row to strings and check for "Ссылка"
                row_values = df.iloc[i].astype(str)
                if any("Ссылка".lower() in str(val).lower() or "ссылка".lower() in str(val).lower() for val in row_values):
                    additional_header_row = i
                    break  # Take the first match, or adjust to collect all if needed

        # Step 4: Merge header rows if additional_header_row is found
        if additional_header_row is not None:
            # Get the two rows to merge
            row1 = df.iloc[header_row].copy()
            row2 = df.iloc[additional_header_row].copy()

            # Merge the rows: use row1 value if not NaN, otherwise use row2 value
            merged_header = row1.where(row1.notna(), row2)

            # Update the DataFrame with the merged header row
            df.iloc[header_row] = merged_header
            # Drop the additional header row since it's merged
            df = df.drop(additional_header_row).reset_index(drop=True)

        # Step 5: Set the headers
        new_header = df.iloc[header_row]  # Row with potential (merged) headers
        df = df[header_row + 1:]  # Data starts after header
        df.columns = new_header  # Set as column names
        df = df.reset_index(drop=True)  # Reset index after slicing
        # After setting the headers (e.g., df.columns = new_header), add this:
        # After setting the headers (e.g., df.columns = new_header), add this:
        df.columns = [
            col.replace('Ссылка', '').replace('ссылка', '').replace('.', '').replace(',', '').strip() if isinstance(col,
                                                                                                                    str) else col
            for col in df.columns]

        return df










def find_date_column(df):
    date_column = None

    # Step 1: Search for date patterns in all columns (no dtype check)
    for column in df.columns:
        # Get the first 10 non-NaN values (or all if fewer exist)
        sample_values = df[column].dropna().head(10).values.tolist()

        if not sample_values:  # Skip if no non-NaN values
            continue

        date_count = 0
        total_values = len(sample_values)

        for value in sample_values:
            try:
                # Try to parse the value as a date
                parse(str(value), fuzzy=True)
                date_count += 1
            except (ValueError, TypeError):
                continue

        # If more than 50% of the sample values look like dates, consider it a date column
        if date_count / total_values >= 0.8:
            date_column = column
            print(
                f"Found potential date column: {column} (based on {date_count}/{total_values} values parsing as dates)")
            return column

    if date_column is None:
        print("No column with date-like values found. Check data formats or patterns.")
        return None









def dates_fixer(df,date_column):
    if date_column not in df.columns:
        raise KeyError(f"Column '{date_column}' not found in DataFrame")
    else:
        print(f"Selected date column: {date_column}")
        # Convert the date column to datetime using dateutil.parser for flexibility
        df[date_column] = df[date_column].apply(
        lambda x: pd.to_datetime(parse(str(x), fuzzy=True), errors='coerce') if pd.notna(x) else pd.NaT)
        print(f"Converted {date_column} to datetime format. Sample: {df[date_column].head()}")
        df.set_index(date_column, inplace=True)
        df.index = df.index.floor('s')
        print(f"Number of nan in index is {df.index.isna().sum()}")

    return df


def detect_product_column(df):
    # Common product keywords/patterns in Russian based on your data
    product_keywords = ['труба', 'лист', 'уголок', 'круг', 'полоса', 'арматура', 'швеллер', 'проф']

    best_column = None
    highest_match_count = 0

    # Check each column
    for col_idx, col_name in enumerate(df.columns):
        # Take just 10 sample rows
        sample_size = min(10, len(df))
        sample_values = df.iloc[:sample_size, col_idx]

        # Count keyword matches
        matches = 0
        for value in sample_values:
            # Skip empty values
            if value is None:
                continue

            # Convert to string for comparison
            value_str = str(value)

            # Count if any product keyword appears in this value
            if any(keyword in value_str.lower() for keyword in product_keywords):
                matches += 1

        # If this column has more matches than previous best, update
        if matches > highest_match_count:
            highest_match_count = matches
            best_column = (col_idx, col_name)

    # Return the best column if we found a reasonable match
    if best_column and highest_match_count >= 3:  # At least 3 matches to be confident
        return best_column

    # Simple fallback based on column position
    # In many datasets, the 3rd column often contains product descriptions
    if len(df.columns) > 2:
        return 2, df.columns[2]

    return None, None  # No product column detected


def clean_product_name(product_name):
    if not product_name or pd.isna(product_name):
        return ""
    # Convert to string, lowercase, and trim extra whitespace
    product_name = str(product_name).lower().strip()
    # Replace multiple spaces with a single space
    product_name = re.sub(r'\s+', ' ', product_name)
    # Normalize decimal separators first (e.g., "1,5" to "1.5")
    product_name = re.sub(r'(\d+),(\d+)', r'\1.\2', product_name)
    # Remove commas and semicolons
    product_name = re.sub(r'[,;]', '', product_name)
    # Remove periods that are not part of a number
    product_name = re.sub(r'(?<!\d)\.(?!\d)', '', product_name)
    # Replace abbreviation periods (a period following a letter and preceding a digit) with a space
    product_name = re.sub(r'(?<=[^\d\s])\.(?=\d)', ' ', product_name)
    # Replace 'x' (or Cyrillic 'х') with '*' only when it's between digits
    product_name = re.sub(r'(?<=\d)\s*[xх]\s*(?=\d)', '*', product_name)
    # Collapse any extra spaces that may have been introduced
    product_name = re.sub(r'\s+', ' ', product_name)
    return product_name
















def extract_product_type_and_specs(cleaned_name):
    """
    Splits the cleaned_name into:
      - product_type: everything before the first digit (after cleaning trailing punctuation/spaces)
      - specs: the first contiguous non-space block starting from the first digit.

    For example, given:
      "Труба Проф 40*20*1,5 L=6"
    it will return:
      ("Труба Проф", "40*20*1,5")
    """
    match = re.search(r'\d', cleaned_name)
    if match:
        index = match.start()
        product_type = cleaned_name[:index].rstrip('., ').strip()
        # Split the remainder on spaces and take the first token
        specs = cleaned_name[index:].strip().split()[0]
        return product_type, specs
    return cleaned_name, ''





def clean_numeric_columns(df):
    # Function to clean a single value (remove spaces, replace commas with dots)
    def clean_value(value):
        if isinstance(value, str):
            return value.replace(' ', '').replace(',', '.')
        return value

    # Function to check if a column contains numeric-like strings
    def is_numeric_like(col):
        # Sample a few non-null values (up to 10) to avoid processing the entire column
        sample = col.dropna().head(10)
        if len(sample) == 0:  # Skip empty columns
            return False
        # Clean the sample values and try to convert to float
        try:
            cleaned_sample = [clean_value(val) for val in sample]
            # Try converting all cleaned values to float
            [float(val) for val in cleaned_sample]
            return True
        except (ValueError, TypeError):
            return False

    # Identify columns that are numeric-like (strings that can be converted to numbers)
    numeric_cols = [col for col in df.columns if is_numeric_like(df[col])]

    # Apply cleaning to identified numeric columns
    for col in numeric_cols:
        print(f"Cleaning column: {col}")
        df[col] = df[col].astype(str).str.replace(' ', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        # Round to 2 decimal places (optional, based on your previous requirement)
        df[col] = df[col].round(2)
    # Print the identified numeric columns
    print("Identified numeric columns:", numeric_cols)

    return df

def optimize_dataframe(df):
    """Reduce memory usage of the DataFrame by optimizing data types"""

    # Convert object types to categories when appropriate
    for col in df.select_dtypes(include=['object']).columns:
        # If the column has relatively few unique values, convert to category
        if df[col].nunique() < len(df) * 0.5:  # If less than 50% of values are unique
            df[col] = df[col].astype('category')

    # Downcast numeric columns
    for col in df.select_dtypes(include=['int']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')

    for col in df.select_dtypes(include=['float']).columns:
        df[col] = pd.to_numeric(df[col], downcast='float')

    return df

def time_selector(branch_df):
    # Convert index to datetime if it's not already
    if not isinstance(branch_df.index, pd.DatetimeIndex):
        st.error("DataFrame index is not a DatetimeIndex. Please ensure your index contains dates.")
        return branch_df

    # Get min and max dates from index
    min_date = branch_df.index.min().date()
    max_date = branch_df.index.max().date()

    # Create date input
    date_range = st.date_input(
        "Выберите временной диапазон",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Check if user has selected a range (two dates)
    if len(date_range) == 2:
        start_date, end_date = date_range
        # Convert to Timestamp for proper comparison with DatetimeIndex
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # End of day

        # Filter dataframe
        filtered_df = branch_df[(branch_df.index >= start_ts) & (branch_df.index <= end_ts)]

        # Display selected range information
        st.write(f"Выбран период с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}")
        st.write(f"Количество записей: {len(filtered_df)}")

        return filtered_df
    else:
        st.info("Пожалуйста, выберите конечную дату диапазона")
        return branch_df