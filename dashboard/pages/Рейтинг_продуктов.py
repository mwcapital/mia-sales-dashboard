from operator import truediv
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from панель_продаж import optimize_dataframe
import pydeck as pdk
import numpy as np
import plotly.graph_objects as go


if 'branch_df' in st.session_state:
    # Retrieve the DataFrame
    branch_df = st.session_state['branch_df']

    # Now you can use the DataFrame
    st.write(f"данные имеют {len(branch_df)} строк и {len(branch_df.columns)} столбцы")
else:
    st.error("Данные не найдены в состоянии сеанса. Пожалуйста, перейдите на первую страницу, чтобы загрузить данные.")


################# Calculate cutoff date if you wish to limit the data

###################### Add st.pills for selecting values in the 'Склад' column######################################
warehouse_options = list(branch_df['Склад'].unique())
with st.expander('Склад'):
    selected_warehouses = st.pills(
        label="Выберите склад(ы)",
        options=warehouse_options,
        selection_mode='multi',
        default=None  # Start with no selections
    )
@st.cache_data
def select_warehouse(branch_df):
    # Filter the DataFrame based on selected warehouses
    if selected_warehouses:
        branch_df = branch_df[branch_df['Склад'].astype(str).isin(selected_warehouses)]
        return branch_df
    else:
        return branch_df
branch_df=select_warehouse(branch_df)

#######################("3D Product Analysis")
st.header("3D-анализ продукции за определенный период времени")

# Time range selector
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
branch_df=time_selector(branch_df)


# Metric selection
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

# Product type selection
all_product_types = branch_df["продукция"].unique().tolist()
product_type_options = ["Вся продукция"] + all_product_types
selected_product_type = st.selectbox("Выберите продукцию", product_type_options)

# Determine if we're showing product types or specifications
if selected_product_type != "Вся продукция":
    # Filter for the selected product type
    filtered_df = branch_df[branch_df["продукция"] == selected_product_type]

    # Group by product_spec
    if selected_metric == 'Count':
        grouped_data = filtered_df.groupby("вид продукции").size().reset_index(name=selected_metric)
    else:
        grouped_data = filtered_df.groupby("вид продукции")[selected_metric].sum().reset_index()

    # Rename columns for clarity
    grouped_data.rename(columns={'вид продукции': 'категория'}, inplace=True)
    category_label = "Product Specification"
    title = f"Лучший тип продукта {selected_product_type} по {metric_options[selected_metric]}"
else:
    # Group by product_type
    if selected_metric == 'Count':
        grouped_data = branch_df.groupby("продукция").size().reset_index(name=selected_metric)
    else:
        grouped_data = branch_df.groupby("продукция")[selected_metric].sum().reset_index()

    # Rename columns for clarity
    grouped_data.rename(columns={"продукция": 'категория'}, inplace=True)
    category_label = "продукция"
    title = f"Лучшая продукция по {metric_options[selected_metric]}"
# Sort data by the selected metric
grouped_data = grouped_data.sort_values(selected_metric, ascending=False).reset_index(drop=True)

# Total number of categories available for the slider to display the window of products chosen
total_items = len(grouped_data)
if total_items == 1:
    st.info("Доступен только один товар — отображается этот товар.")
    grouped_data = grouped_data  # Use the single item
    selection_title = "Одиночный предмет"
else:
    # Create a list of indices for the select slider
    indices = list(range(total_items))
    # Create a select slider for range selection
    start_idx, end_idx = st.select_slider(
        "Выберите диапазон элементов для отображения",
        options=indices,
        value=(0, min(15, total_items - 1)),
    )

    # Calculate how many items we're selecting
    items_count = end_idx - start_idx + 1
    # Select the range from the data
    grouped_data = grouped_data.iloc[start_idx:end_idx + 1]











# Create 3D bars using separate traces for each bar
fig = go.Figure()
# Calculate grid positions for the bars
num_items = len(grouped_data)
grid_size = int(np.ceil(np.sqrt(num_items)))
# Colors for the bars (using a blue color scale)
qualitative_colors = [
    'rgb(166,206,227)', 'rgb(31,120,180)', 'rgb(178,223,138)',
    'rgb(51,160,44)', 'rgb(251,154,153)', 'rgb(227,26,28)',
    'rgb(253,191,111)', 'rgb(255,127,0)', 'rgb(202,178,214)',
    'rgb(106,61,154)', 'rgb(255,255,153)', 'rgb(177,89,40)'
]
# Repeat the colors if we have more bars than colors
bar_colors = [qualitative_colors[i % len(qualitative_colors)] for i in range(num_items)]

# Keep track of category positions
category_positions = {}

# Add bars one by one
for index, (idx, row) in enumerate(grouped_data.iterrows()):
    x_pos = index % grid_size
    y_pos = index // grid_size
    category_positions[row['категория']] = (x_pos, y_pos)

    # Format hover text
    if selected_metric == 'Сумма':
        formatted_value = f"{row[selected_metric]:,.0f} ₸"
    else:
        formatted_value = f"{row[selected_metric]:,.0f}"

    hover_text = f"{row['категория']}<br>{metric_options[selected_metric]}: {formatted_value}"

    # Use a fixed color for all bars or vary by index
    bar_color = bar_colors[index % len(bar_colors)]  # Use the bar's index, not i

    # Add a simple box trace
    fig.add_trace(go.Scatter3d(
        x=[x_pos, x_pos + 0.7, x_pos + 0.7, x_pos, x_pos],
        y=[y_pos, y_pos, y_pos + 0.7, y_pos + 0.7, y_pos],
        z=[row[selected_metric], row[selected_metric], row[selected_metric], row[selected_metric],
           row[selected_metric]],
        mode='lines',
        line=dict(color=bar_color, width=6),
        surfaceaxis=2,  # This tells it to fill the z-axis surface
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Bottom of the box
    fig.add_trace(go.Scatter3d(
        x=[x_pos, x_pos + 0.7, x_pos + 0.7, x_pos, x_pos],
        y=[y_pos, y_pos, y_pos + 0.7, y_pos + 0.7, y_pos],
        z=[0, 0, 0, 0, 0],
        mode='lines',
        line=dict(color=bar_color, width=6),
        surfaceaxis=2,  # This tells it to fill the z-axis surface
        showlegend=False
    ))

    # Connect top to bottom with lines at the corners
    for corner_x, corner_y in [(x_pos, y_pos), (x_pos + 0.7, y_pos), (x_pos + 0.7, y_pos + 0.7), (x_pos, y_pos + 0.7)]:
        fig.add_trace(go.Scatter3d(
            x=[corner_x, corner_x],
            y=[corner_y, corner_y],
            z=[0, row[selected_metric]],
            mode='lines',
            line=dict(color=bar_color, width=6),
            showlegend=False
        ))

    # Add text label on top of the bar
    fig.add_trace(go.Scatter3d(
        x=[x_pos + 0.35],
        y=[y_pos + 0.35],
        z=[row[selected_metric] * 1.05],  # Slightly above the bar
        mode='text',
        text=[row['категория'][:10] + '...' if len(row['категория']) > 10 else row['категория']],
        textposition='top center',
        textfont=dict(
            size=16,  # Increase font size (default is 12)
            family="Times New Roman Bold"  # Use a bold font family
            # color=white  # Ensure good contrast
        ),
        showlegend=False,

    ))


# Update layout with conditional axis formatting based on selected metric
if selected_metric == 'Сумма':
    z_axis_title = f"{metric_options[selected_metric]} (₸)"
    z_tickformat = ",.0f"  # Thousands separator, no decimal places
elif selected_metric == 'Количество':
    z_axis_title = f"{metric_options[selected_metric]} (кг)"
    z_tickformat = ",.0f"  # Thousands separator, no decimal places
else:
    z_axis_title = metric_options[selected_metric]
    z_tickformat = ",.0f"  # Thousands separator, no decimal places

fig.update_layout(
    scene=dict(
        xaxis=dict(
            title='',
            showticklabels=False,
            showgrid=True,
            zeroline=True,
            range=[-1, grid_size]
        ),
        yaxis=dict(
            title='',
            showticklabels=False,
            showgrid=True,
            zeroline=True,
            range=[-1, grid_size]
        ),
        zaxis=dict(
            title=z_axis_title,  # Use the conditional title with appropriate unit
            showgrid=True,
            zeroline=True,
            tickformat=z_tickformat  # Add thousands separators
        ),
        camera=dict(
            eye=dict(x=1.5, y=1.5, z=1.2)
        ),
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=1.2)
    ),
    margin=dict(l=0, r=0, b=0, t=40),
    height=600
)

# Display the plot
st.plotly_chart(fig, use_container_width=True)
