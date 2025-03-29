from operator import truediv
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from панель_продаж import optimize_dataframe

# Check if the DataFrame exists in session state
if 'branch_df' in st.session_state:
    # Retrieve the DataFrame
    branch_df = st.session_state['branch_df']

    # Now you can use the DataFrame
    st.write(f"данные имеют {len(branch_df)} строк и {len(branch_df.columns)} столбцы")
else:
    st.error("Данные не найдены в состоянии сеанса. Пожалуйста, перейдите на первую страницу, чтобы загрузить данные.")



################# Calculate cutoff date if you wish to limit the data


st.info(f"Анализ данных c {branch_df.index.min().strftime('%b %Y')} по {branch_df.index.max().strftime('%b %Y')}")




#############separate into type and spec
type_options=['Все']+list(branch_df["продукция"].unique())
selected_types = st.multiselect("Выберите продукцию", type_options)
if "Все" in selected_types or not selected_types:
    branch_df = branch_df  # If "All" is selected or nothing is selected, show all specs
else:
    branch_df = branch_df[branch_df["продукция"].isin(selected_types)]

# Add "All" option for product spec selection
spec_options = ["Все"] + list(branch_df["вид продукции"].unique())
selected_specs = st.multiselect("Выберите вид продукции", spec_options)
# Apply filtering logic for product specs
if "Все" in selected_specs or not selected_specs:
    branch_df = branch_df  # If "All" is selected or nothing is selected, show all specs
else:
    branch_df = branch_df[branch_df["вид продукции"].isin(selected_specs)]




###################### Add st.pills for selecting values in the 'Склад' column
warehouse_options = list(branch_df['Склад'].unique())
with st.expander('Склад'):
    selected_warehouses = st.pills(
        label="Выберите Склад",
        options=warehouse_options,
        selection_mode='multi',
        default=None  # Start with no selections
    )

# Filter the DataFrame based on selected warehouses
if selected_warehouses:
    branch_df = branch_df[branch_df['Склад'].astype(str).isin(selected_warehouses)]
else:
    branch_df = branch_df  # No filtering if no warehouses are selected



########display the data to be able to see
st.data_editor(
    branch_df,
    column_config={"Сумма":st.column_config.NumberColumn(
            "Сумма", help="The deal value in KZT", format="₸ %.2f"),
        "Количество": st.column_config.NumberColumn(
            "Количество", help="The weight of the products sold", format="%.2f kg")
    }
)



##################### Metric selection for analysis
metric_options = {
    'Сумма': 'Oбъем продаж',
    'Количество': 'Количество в кг.',
    'Count': 'Количество сделок'
}

selected_metric = st.selectbox(
    "Выберите метрику",
    options=list(metric_options.keys()),
    format_func=lambda x: metric_options[x]  # Display the friendly name in the dropdown
)

# Add units to the label
# 1. Monthly Analysis
if selected_metric == 'Count':
    monthly_data = branch_df.groupby('ГодМесяц').agg({
        'product': 'count'  # Count the number of transactions
    })
else:
    # For 'Сумма' or 'Количество', sum the values
    monthly_data = branch_df.groupby('ГодМесяц').agg({
        selected_metric: 'sum'
    })

# 2. Quarterly Analysis
if selected_metric == 'Count':
    quarterly_data = branch_df.groupby('ГодЧетверть').agg({
        'product': 'count'  # Count the number of transactions
    })
else:
    # For 'Сумма' or 'Количество', sum the values
    quarterly_data = branch_df.groupby('ГодЧетверть').agg({
        selected_metric: 'sum'
    })

# 3. Yearly Analysis
if selected_metric == 'Count':
    yearly_data = branch_df.groupby('Год').agg({
        'product': 'count'  # Count the number of transactions
    })
else:
    # For 'Сумма' or 'Количество', sum the values
    yearly_data = branch_df.groupby('Год').agg({
        selected_metric: 'sum'
    })

############################### Visualizations TIME SERIES BARS#######################################
# Create a branch title for the header
time_period = st.radio("Select Time Period", ['Ежемесячно', 'Ежеквартально', 'Ежегодно'])

# Select the data and x-axis column based on the time period
if time_period == 'Ежемесячно':
    data = monthly_data
    x_col = monthly_data.index
    x_title = 'Месяц'
    # filter for the time
    start_date, end_date = st.select_slider(
        "Выберите временной диапазон",options=list(data.index),
        value=(data.index.min(), data.index.max())
    )
    st.write("Вы выбрали данные между", start_date, "и", end_date)
    data = data[(data.index >= start_date) & (data.index <= end_date)]

elif time_period == 'Ежеквартально':
    data = quarterly_data
    x_col = quarterly_data.index
    x_title = 'Четверть'
    # filter for the time
    start_date, end_date = st.select_slider(
        "Выберите временной диапазон", options=list(data.index),
        value=(data.index.min(), data.index.max())
    )
    st.write("Вы выбрали данные между", start_date, "и", end_date)
    data = data[(data.index >= start_date) & (data.index <= end_date)]
else:  # Yearly
    data = yearly_data
    x_col = yearly_data.index
    x_title = 'Год'
    # filter for the time
    start_date, end_date = st.select_slider(
        "Выберите временной диапазон", options=list(data.index),
        value=(data.index.min(), data.index.max())
    )
    st.write("Вы выбрали данные между", start_date, "и", end_date)
    data = data[(data.index >= start_date) & (data.index <= end_date)]

#add growth rate
data['Growth Rate']=data.pct_change()


# Add a checkbox to toggle the growth rate line
st.subheader(f"{time_period} , {selected_metric} , {st.session_state.branch_title} , {selected_warehouses}, {selected_types} , {selected_specs}")

tab1, tab2 = st.tabs(["📈 график", "🗃 данные"])
tab1.bar_chart(data,use_container_width=True,y_label="Oбъем продаж в ₸")
tab1.bar_chart(data["Growth Rate"], use_container_width=True)
tab2.table(data)
