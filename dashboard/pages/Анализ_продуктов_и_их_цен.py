import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta

from pygments.lexer import default

from functions import time_selector
if 'branch_df' in st.session_state:
    # Retrieve the DataFrame
    branch_df = st.session_state['branch_df']

    # Now you can use the DataFrame
    st.write(f"данные имеют {len(branch_df)} строк и {len(branch_df.columns)} столбцы")
else:
    st.error("Данные не найдены в состоянии сеанса. Пожалуйста, перейдите на первую страницу, чтобы загрузить данные.")




# 1. First check if the columns exist and that 'Сумма' & 'Количество' are numeric
if 'Сумма' in branch_df.columns and 'Количество' in branch_df.columns:
    branch_df = branch_df.dropna(subset=['Сумма', 'Количество'])
    # Check for numeric type
    if pd.api.types.is_numeric_dtype(branch_df['Сумма']) and pd.api.types.is_numeric_dtype(branch_df['Количество']):
        # Replace zeros and NaNs with NaN to avoid division by zero
        denominator = branch_df['Количество'].replace(0, np.nan)

        # Calculate unit price only where denominator is valid
        branch_df['Цена за единицу товара'] = branch_df['Сумма'] / denominator


# Date range filter
branch_df=time_selector(branch_df)



#######TABS FOR ANALYSIS
#TAB NUMBER 1
tab1, tab2 = st.tabs(["Анализ концентрации продукта", "Анализ цен"])
with tab1:
    st.header("Анализ концентрации продукта")

    # 1. Calculate product mix percentages
    product_revenue = branch_df.groupby("продукция")['Сумма'].sum().reset_index()
    total_revenue = product_revenue['Сумма'].sum()
    product_revenue['Процент'] = (product_revenue['Сумма'] / total_revenue * 100).round(2)
    product_revenue = product_revenue.sort_values('Сумма', ascending=False)
    # Display top products by revenue
    st.subheader('Продукция, отсортированная по доходу')
    # Choose visualization type
    viz_type = st.radio("Select Visualization", ["Bar Chart", "Pie Chart", "Treemap"], horizontal=True)
    # Set number of products to display
    top_n = st.slider("Количество отображаемых продуктов", 5, 40, 5, 1)
    top_products = product_revenue.head(top_n)
    st.table(top_products)
    if viz_type == "Bar Chart":
        fig = px.bar(
            top_products,
            x="продукция",
            y='Сумма',
            text='Процент',
            labels={"продукция": 'Продукция', 'Сумма': 'Доход'},
            title=f"Toп {top_n} Продукции по доходам"
        )
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    elif viz_type == "Pie Chart":
        fig = px.pie(
            top_products,
            values='Сумма',
            names="продукция",
            title=f"Toп {top_n} Продукции по доходам",
            hole=0.4
        )
        fig.update_traces(textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    else:  # Treemap
        fig = px.treemap(
            top_products,
            path=["продукция"],
            values='Сумма',
            title=f"Toп {top_n} Продукции по доходам",
            color='Процент',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 2. Track changes in product mix over time
    st.subheader("Эволюция доходной продукции с течением времени")

    time_period = st.radio("Период времени", ['Ежемесячно', 'Ежеквартально', 'Ежегодно'], horizontal=True)

    if time_period == 'Ежемесячно':
        period_col = 'ГодМесяц'
    elif time_period == 'Ежеквартально':
        period_col = 'ГодЧетверть'
    else:
        period_col = 'Год'

    # Get top products for time series analysis
    top_k = st.slider("Количество отображаемых продуктов", 5, 15, 5, 1)
    top_product_types = product_revenue.head(top_k)["продукция"].tolist()
    # top_product_types = product_revenue.head(50)["продукция"].tolist()
    # Filter to just the top products
    time_df = branch_df[branch_df["продукция"].isin(top_product_types)]
    # Group by Период времени and Продукция
    product_time_series = time_df.groupby([period_col, "продукция"])['Сумма'].sum().reset_index()

    # Create a pivot for easier plotting
    pivot_df = product_time_series.pivot(index=period_col, columns="продукция", values='Сумма').fillna(0)
    pivot_df['Всего'] = pivot_df.sum(axis=1)

    # Calculate percentages
    for col in pivot_df.columns:
        if col != 'Всего':
            pivot_df[f"{col}_прц"] = (pivot_df[col] / pivot_df['Всего'] * 100).round(2)

    # Plot the evolution
    viz_type = st.radio("Вид", ["Абсолютные показания", "Процентная смесь"], horizontal=True, key="time_view")

    if viz_type == "Абсолютные показания":
        # Create a stacked bar chart for Абсолютные показания
        fig = go.Figure()

        for product in top_product_types:
            if product in pivot_df.columns:  # Safety check
                fig.add_trace(go.Bar(
                    x=pivot_df.index,
                    y=pivot_df[product],
                    name=product
                ))

        fig.update_layout(
            barmode='stack',
            title=f"Доход от продукта с течением времени ({time_period})",
            xaxis_title="Период времени",
            yaxis_title="Доход",
            legend_title="Продукция"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        # Create a 100% stacked area chart for percentages
        # Fix: use '_прц' suffix instead of '_pct'
        percent_cols = [f"{col}_прц" for col in top_product_types if f"{col}_прц" in pivot_df.columns]
        percent_df = pivot_df[percent_cols].copy()

        # Rename columns to remove the suffix for cleaner legend
        percent_df.columns = [col.replace('_прц', '') for col in percent_cols]

        fig = px.area(
            percent_df,
            title=f"Эволюция доходной продукции с течением времени ({time_period})",
            labels={"value": "Процент", "variable": "Продукция"}
        )

        fig.update_layout(yaxis=dict(ticksuffix="%"))

        st.plotly_chart(fig, use_container_width=True)

    # 3. Analyze popular specifications
    st.subheader("Анализ популярных типов продукции")

    # Select a Продукция to analyze
    product_for_spec = st.selectbox(
        "Выбор продукции для анализа типа продукции",
        options=product_revenue.head(50)["продукция"].tolist()
    )

    # Filter data for the selected Продукция
    spec_df = branch_df[branch_df["продукция"] == product_for_spec]

    # Get top specifications by quantity and revenue
    spec_analysis = spec_df.groupby("вид продукции").agg({
        'Количество': 'sum',
        'Сумма': 'sum',
        'product': 'count'  # Count of transactions
    }).reset_index()

    spec_analysis.rename(columns={'product': 'Количество_транзакций'}, inplace=True)

    # Sort by different metrics
    sort_by = st.radio("Сортировать по", ["Доход", 'Количество', 'Количество_транзакций'], horizontal=True)

    if sort_by == "Доход":
        spec_analysis = spec_analysis.sort_values('Сумма', ascending=False)
        y_col = 'Сумма'
        title = f"Основные типы продуктов {product_for_spec} по доходам"
    elif sort_by == "Количество":
        spec_analysis = spec_analysis.sort_values('Количество', ascending=False)
        y_col = 'Количество'
        title = f"Основные типы продуктов {product_for_spec} по количеству в кг"
    else:
        spec_analysis = spec_analysis.sort_values('Количество_транзакций', ascending=False)
        y_col = 'Количество_транзакций'
        title = f"Основные типы продуктов {product_for_spec} по количеству транзакций"

    # Limit to top 15 for readability
    top_s = st.slider("Количество отображаемых типов продуктов", 2, 50, 5, 1)
    top_specs = spec_analysis.head(top_s)

    # Create bar chart
    fig = px.bar(
        top_specs,
        x="вид продукции",
        y=y_col,
        title=title,
        labels={"вид продукции": 'типы продуктов', y_col: sort_by}
    )

    fig.update_layout(xaxis_tickangle=-45)

    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Анализ цен")
    # 1. Price Trends Over Time
    st.subheader("Тенденции изменения цен с течением времени")

    # Select product for price analysis
    price_product = st.selectbox(
        "Выберите продукцию",
        options=product_revenue.head(50)["продукция"].tolist(),
        key="price_product"
    )
    # Filter data for selected product
    price_df = branch_df[branch_df["продукция"] == price_product].copy()
    #clear outliers
    price_df = price_df[price_df['Цена'] <= 6 * price_df['Цена'].mean()]

    product_specs = price_df["вид продукции"].unique().tolist()
    # Handle case when no specs are available
    if not product_specs:
        st.warning(f"Тип продукта не найден")
        st.stop()

    # Sort specifications for consistent ordering
    product_specs.sort()
    # Select product specification - default to first specification in the list
    price_product_spec = st.selectbox(
        "Выберите вид продукции",
        options=product_specs,
        index=0,  # Default to first specification
        key="price_product_spec"
    )
    # Filter data for the selected specification
    price_df = price_df[price_df["вид продукции"] == price_product_spec].copy()
    product_title = f"{price_product} ({price_product_spec})"
    st.info(f"показываю тенденции цен для {price_product} со спецификацией: {price_product_spec}")





    # Check if there's enough data
    if len(price_df) < 2:
        st.warning(f"Недостаточно данных для анализа цен {price_product}")
    else:
        # Group by Период времени and calculate average unit price
        time_period = st.radio("Период времени", ['Ежемесячно', 'Ежеквартально', 'Ежегодно'], horizontal=True, key="price_time")

        if time_period == 'Ежемесячно':
            period_col = 'ГодМесяц'
        elif time_period == 'Ежеквартально':
            period_col = 'ГодЧетверть'
        else:
            period_col = 'Год'
        # Check if "Цена по прайсу" column exists in the data
        has_list_price = 'Цена по прайсу' in price_df.columns

        # Calculate price statistics for each period, including list price if available
        if has_list_price:
            price_stats = price_df.groupby(period_col).agg({
                'Цена': ['mean', 'median', 'min', 'max', 'count'],
                'Цена по прайсу': ['mean', 'median'],  # Add list price statistics
                'Сумма': 'sum',
                'Количество': 'sum'
            })

            price_stats.columns = ['Средняя_цена', 'Медиана_цена', 'Мин_цена', 'Макс_цена',
                                   'Количество_транзакций', 'Средняя_цена_по_прайс_листу', 'Медиана_цена_по_прайс_листу',
                                   'Общий_доход', 'Общее_количество']
        else:
            price_stats = price_df.groupby(period_col).agg({
                'Цена': ['mean', 'median', 'min', 'max', 'count'],
                'Сумма': 'sum',
                'Количество': 'sum'
            })

            price_stats.columns = ['Средняя_цена', 'Медиана_цена', 'Мин_цена', 'Макс_цена',
                                   'Количество_транзакций', 'Общий_доход', 'Общее_количество']

        price_stats = price_stats.reset_index()
        st.dataframe(price_df)
        # Calculate overall average for reference
        overall_avg = price_df['Цена'].mean()
        # Add descriptive statistics about the price
        stats_col1, stats_col2, stats_col3 = st.columns(3)
        with stats_col1:
            st.metric("Средняя цена", f"{overall_avg:.2f}")
        with stats_col2:
            price_std = price_df['Цена'].std()
            st.metric("Стандартное отклонение", f"{price_std:.2f}")
        with stats_col3:
            cv = (price_std / overall_avg * 100) if overall_avg > 0 else 0
            st.metric("Коэффициент вариации", f"{cv:.1f}%",
                      help="Более низкие значения указывают на более последовательное ценообразование.")
        # Create main price trend figure
        main_fig = go.Figure()
        # Add price line
        main_fig.add_trace(go.Scatter(
            x=price_stats[period_col],
            y=price_stats['Средняя_цена'],
            mode='lines+markers',
            name='Средняя цена',
            line=dict(color='royalblue', width=2),
            hovertemplate='%{y:.2f}'
        ))

        # Add median price line
        main_fig.add_trace(go.Scatter(
            x=price_stats[period_col],
            y=price_stats['Медиана_цена'],
            mode='lines+markers',
            name='Медиана цена',
            line=dict(color='green', width=2, dash='dot'),
            hovertemplate='%{y:.2f}'
        ))

        # Add overall average reference line
        main_fig.add_trace(go.Scatter(
            x=[price_stats[period_col].iloc[0], price_stats[period_col].iloc[-1]],
            y=[overall_avg, overall_avg],
            mode='lines',
            line=dict(color='red', width=2, dash='dash'),
            name=f'Общее срд ({overall_avg:.2f})'
        ))

        # Add list price comparison if available
        if has_list_price:
            # Add a checkbox to toggle list price display
            show_list_price = st.checkbox("Сравните с ценой по прайсу", value=True)

            if show_list_price:
                # Calculate overall average list price for reference
                overall_list_avg = price_df['Цена по прайсу'].mean()

                # Add dropdown to select which list price metric to show
                list_price_metric = st.radio(
                    "Выберите метрику",
                    ["Среднее", "Медиана"],
                    horizontal=True
                )

                if list_price_metric == "Среднее":
                    list_price_col = 'Средняя_цена_по_прайс_листу'
                    list_price_name = 'Средняя цена по прайс листу'
                else:
                    list_price_col = 'Медиана_цена_по_прайс_листу'
                    list_price_name = 'Медиана цена по прайс листу'

                # Add list price line to the figure
                main_fig.add_trace(go.Scatter(
                    x=price_stats[period_col],
                    y=price_stats[list_price_col],
                    mode='lines+markers',
                    name=list_price_name,
                    line=dict(color='darkorange', width=2, dash='dot'),
                    hovertemplate='%{y:.2f}'
                ))







        # Update layout for main price trend figure
        main_fig.update_layout(
            title=f"Тенденция цен на {product_title} за ({time_period})",
            xaxis_title="Период времени",
            yaxis_title="Цена за единицу",
            legend_title="Ценовые показатели",
            hovermode="x unified",
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=10)
            )
        )

        # If many Период времениs, show every nth label
        if len(price_stats) > 12:
            main_fig.update_xaxes(nticks=12)

        # Display the main price trend chart
        st.plotly_chart(main_fig, use_container_width=True)

        # Add transaction volume as overlay
        show_volume = st.checkbox("Показать количество продаж и цену")

        if show_volume:
            volume_fig = go.Figure()

            # Primary y-axis for price
            volume_fig.add_trace(go.Scatter(
                x=price_stats[period_col],
                y=price_stats['Средняя_цена'],
                mode='lines+markers',
                name='Средняя цена',
                line=dict(color='royalblue', width=2),
                hovertemplate='%{y:.2f}'
            ))

            # Secondary y-axis for volume
            volume_fig.add_trace(go.Bar(
                x=price_stats[period_col],
                y=price_stats['Общее_количество'],
                name='Объем',
                opacity=0.5,
                marker_color='lightgray',
                yaxis='y2',
                hovertemplate='%{y:,.0f} units'
            ))

            volume_fig.update_layout(
                title=f"Цена против объема для {product_title} ({time_period})",
                xaxis_title="Период времени",
                yaxis=dict(
                    title=dict(
                        text="Цена за единицу",
                        font=dict(color='royalblue')
                    ),
                    tickfont=dict(color='royalblue')
                ),
                yaxis2=dict(
                    title=dict(
                        text="Объем",
                        font=dict(color='gray')
                    ),
                    tickfont=dict(color='gray'),
                    anchor="x",
                    overlaying="y",
                    side="right"
                ),
                legend_title="Метрики",
                hovermode="x unified",
                xaxis=dict(
                    tickangle=-45,
                    tickfont=dict(size=10)
                )
            )

            # If many Период времениs, show every nth label
            if len(price_stats) > 12:
                volume_fig.update_xaxes(nticks=12)

            st.plotly_chart(volume_fig, use_container_width=True)


        # Add price distribution histogram
        show_distribution = st.checkbox("Показать дистрибуцию цен")

        if show_distribution:
            dist_fig = px.histogram(
                price_df,
                x="Цена",
                nbins=20,
                histnorm='percent',
                title=f"Дистрибуция цен для {product_title}",
                labels={"Цена за единицу товара": "Цена за единицу", "процент": "Процент транзакций"}
            )

            # Add vertical line for mean
            dist_fig.add_vline(
                x=overall_avg,
                line_dash="dash",
                line_color="red",
                annotation_text=f"среднее: {overall_avg:.2f}",
                annotation_position="top right"
            )

            # Add vertical line for median
            median_price = price_df['Цена'].median()
            dist_fig.add_vline(
                x=median_price,
                line_dash="dash",
                line_color="green",
                annotation_text=f"медиана: {median_price:.2f}",
                annotation_position="top left"
            )

            # Display the distribution chart
            st.plotly_chart(dist_fig, use_container_width=True)

        # Add filters to narrow down data if needed
        show_transaction_scatter = st.checkbox("Показать график сделок (цена/количество)", value=True)
        if show_transaction_scatter:
            # Create scatter plot
            fig = go.Figure()

            # Add scatter plot with Unit_Price vs Quantity
            fig.add_trace(go.Scatter(
                x=price_df['Количество'],  # X-axis is now quantity
                y=price_df['Цена'],  # Y-axis is now unit price
                mode='markers',
                marker=dict(
                    size=10,  # Fixed size for better readability
                    color='royalblue',
                    opacity=0.7,
                    line=dict(width=1, color='darkblue')
                ),
                text=price_df.apply(
                    lambda row: f"Дата: {row.name.strftime('%d.%m.%Y')}<br>" +
                                f"Цена: {row['Цена']:.2f} ₸<br>" +
                                f"Сумма: {row['Сумма']:,.0f} ₸<br>" +
                                f"Количество: {row['Количество']:,.1f} кг",
                    axis=1
                ),
                hoverinfo='text'
            ))

            # Calculate average price
            avg_price = price_df['Цена'].mean()
            median_price = price_df['Цена'].median()

            # Add reference lines for average and median price
            fig.add_shape(
                type="line",
                x0=price_df['Количество'].min(), x1=price_df['Количество'].max(),
                y0=avg_price, y1=avg_price,
                line=dict(color="red", width=2, dash="dash"),
            )

            fig.add_shape(
                type="line",
                x0=price_df['Количество'].min(), x1=price_df['Количество'].max(),
                y0=median_price, y1=median_price,
                line=dict(color="green", width=2, dash="dash"),
            )

            # Add annotations for the lines
            fig.add_annotation(
                x=price_df['Количество'].max(),
                y=avg_price,
                text=f"Средняя цена: {avg_price:.2f} ₸",
                showarrow=True,
                arrowhead=1,
                ax=-50,
                ay=0,
                font=dict(color="red")
            )

            fig.add_annotation(
                x=price_df['Количество'].max(),
                y=median_price,
                text=f"Медианная цена: {median_price:.2f} ₸",
                showarrow=True,
                arrowhead=1,
                ax=-50,
                ay=30,
                font=dict(color="green")
            )

            # Add trend line (power law: y = ax^b often fits price-quantity relationships)
            if len(price_df) > 2:
                try:
                    # Take logs for power law regression (log y = log a + b log x)
                    log_x = np.log(price_df['Количество'].replace(0, 0.1))  # Avoid log(0)
                    log_y = np.log(price_df['Цена'])
                    mask = np.isfinite(log_x) & np.isfinite(log_y)

                    if sum(mask) > 2:  # Need at least 3 valid points
                        from scipy import stats

                        slope, intercept, r_value, p_value, std_err = stats.linregress(
                            log_x[mask], log_y[mask]
                        )

                        # Add power law curve
                        x_range = np.linspace(
                            max(0.1, price_df['Количество'].min()),
                            price_df['Количество'].max(),
                            100
                        )
                        y_range = np.exp(intercept) * x_range ** slope

                        fig.add_trace(go.Scatter(
                            x=x_range, y=y_range,
                            mode='lines',
                            line=dict(color='black', width=2),
                            name=f'Trend (R²: {r_value ** 2:.2f})'
                        ))

                        # Add trend description
                        if slope < -0.05:
                            trend_desc = f"Обнаружена отрицательная зависимость: при увеличении объема цена снижается (скидка за объем)"
                        elif slope > 0.05:
                            trend_desc = f"Обнаружена положительная зависимость: при увеличении объема цена растет"
                        else:
                            trend_desc = f"Зависимость цены от объема практически отсутствует"

                        st.info(trend_desc)
                except Exception as e:
                    st.warning(f"Не удалось рассчитать линию тренда: {e}")

            # Update layout
            fig.update_layout(
                title=f"Цена за единицу в зависимости от объема для {product_title}",
                xaxis=dict(
                    title="Объем (кг)",
                    tickformat=",.0f",
                    type="log" if st.checkbox("Логарифмическая шкала по X", value=True) else "linear"
                ),
                yaxis=dict(
                    title="Цена за единицу (₸)",
                    tickformat=",.2f",
                ),
                hovermode='closest'
            )

            # Show the plot
            st.plotly_chart(fig, use_container_width=True)

            # Add correlation info
            corr = price_df['Цена'].corr(price_df['Количество'])
            st.metric("Корреляция цена-количество", f"{corr:.2f}")

            # Additional explanation
            st.caption("""
            На данном графике:
            - Ось X: Объем продаж в кг
            - Ось Y: Цена за единицу (₸)
            - Каждая точка представляет отдельную сделку
            - Красная линия: средняя цена за единицу
            - Зеленая линия: медианная цена за единицу
            - Черная линия: тренд зависимости цены от объема
            """)