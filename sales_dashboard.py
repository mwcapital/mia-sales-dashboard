import streamlit as st
import pandas as pd
import plotly.express as px

# Streamlit file uploader
st.sidebar.header("Upload File")
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type=["csv"], help="Please upload your sales data file.")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, engine="c", sep=';', encoding="cp1251")

    # Ensure Date column is properly formatted
    df.set_index("Date", inplace=True)
    df.index = pd.to_datetime(df.index, errors="coerce", dayfirst=True)
    df = df.sort_index(ascending=True)

    # Sidebar Filters
    st.sidebar.header("Filter Options")
    selected_product = st.sidebar.selectbox("Select a Product", df["Product Name"].unique(), index=0, help="Type to search", key="product_search")
    
    # Dynamically filter cities based on selected product
    available_cities = df[df["Product Name"] == selected_product]["City"].unique()
    selected_cities = st.sidebar.multiselect("Select Cities to Plot", available_cities, default=available_cities)
    separate_plots = st.sidebar.checkbox("Display separate plots for each city")

    date_range = st.sidebar.date_input("Select Date Range", [df.index.min(), df.index.max()])

    # Apply Filters
    filtered_df = df[df["Product Name"] == selected_product]
    filtered_df = filtered_df[filtered_df["City"].isin(selected_cities)]
    filtered_df = filtered_df[(filtered_df.index >= pd.to_datetime(date_range[0])) & (filtered_df.index <= pd.to_datetime(date_range[1]))]

    # Aggregate Data by City and Date
    sales_over_time = filtered_df.groupby([filtered_df.index, "City"])["Quantity"].sum().reset_index()
    sales_over_time.columns = ['Date', 'City', 'Quantity']
    sales_over_time['Date'] = pd.to_datetime(sales_over_time['Date']).dt.strftime('%Y-%m-%d')  # Format dates correctly

    # Display Metrics
    st.title("📊 Sales Dashboard")
    st.write(f"### Product: {selected_product}")

    st.metric("Total Quantity Sold", int(filtered_df["Quantity"].sum()))
    

    # Create Interactive Charts
    if separate_plots:
        for city in selected_cities:
            city_data = sales_over_time[sales_over_time['City'] == city]
            fig = px.line(city_data, x="Date", y="Quantity", markers=True, title=f"Quantity Sold Over Time - {city}")
            fig.update_layout(xaxis_title="Date", yaxis_title="Quantity Sold")
            st.plotly_chart(fig)
    else:
        fig = px.line(sales_over_time, x="Date", y="Quantity", color="City", markers=True, title="Quantity Sold Over Time by City")
        fig.update_layout(xaxis_title="Date", yaxis_title="Quantity Sold")
        st.plotly_chart(fig)

    # Display the filtered dataframe
    st.write("### Filtered Data")
    st.dataframe(filtered_df)
    