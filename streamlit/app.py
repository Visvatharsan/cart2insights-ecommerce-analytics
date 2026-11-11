import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import pandas as pd



st.set_page_config(
    page_title="Cart2Insights",
    page_icon="🛒",
    layout="wide"
)

@st.cache_resource
def get_engine():
    connection_url = URL.create(
        drivername="mysql+pymysql",
        username=st.secrets["mysql"]["username"],
        password=st.secrets["mysql"]["password"],
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        database=st.secrets["mysql"]["database"]
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True
    )

@st.cache_data
def load_table_names():
    query="SHOW TABLES;"
    tables=pd.read_sql(query,get_engine())

    tables.columns=["table_name"]
    return tables

@st.cache_data(ttl=600)
def load_overview_metrics():
    query = """
        SELECT
            COUNT(*) AS total_orders,
            ROUND(SUM(gross_order_value), 2) AS total_gross_order_value,
            ROUND(AVG(gross_order_value), 2) AS average_gross_order_value
        FROM (
            SELECT
                o.order_id,
                SUM(oi.price + oi.freight_value) AS gross_order_value
            FROM orders AS o
            JOIN order_items AS oi
                ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY o.order_id
        ) AS delivered_orders;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_monthly_revenue():
    query = """
        SELECT
            DATE_FORMAT(o.order_purchase_timestamp, '%%Y-%%m') AS month,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS gross_order_value
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%%Y-%%m')
        ORDER BY month;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_top_categories():
    query = """
        SELECT
            COALESCE(
                ct.product_category_name_english,
                p.product_category_name,
                'Unknown'
            ) AS category,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS gross_order_value
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        JOIN products AS p
            ON oi.product_id = p.product_id
        LEFT JOIN category_translation AS ct
            ON p.product_category_name = ct.product_category_name
        WHERE o.order_status = 'delivered'
        GROUP BY
            ct.product_category_name_english,
            p.product_category_name
        ORDER BY gross_order_value DESC
        LIMIT 10;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_revenue_by_state():
    query = """
        SELECT
            c.customer_state AS state,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS gross_order_value
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        JOIN customers AS c
            ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_state
        ORDER BY gross_order_value DESC;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_top_products():
    query = """
        SELECT
            oi.product_id,
            COUNT(*) AS units_sold,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS gross_order_value
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY oi.product_id
        ORDER BY units_sold DESC, gross_order_value DESC
        LIMIT 10;
    """

    top_products = pd.read_sql(query, get_engine())

    top_products["product_label"] = (
        top_products["product_id"].str[:8] + "..."
    )
    return top_products



@st.cache_data(ttl=600)
def load_customer_type_counts():
    query = """
        WITH customer_orders AS (
            SELECT
                c.customer_unique_id,
                COUNT(DISTINCT o.order_id) AS order_count
            FROM customers AS c
            JOIN orders AS o
                ON c.customer_id = o.customer_id
            WHERE o.order_status = 'delivered'
            GROUP BY c.customer_unique_id
        )
        SELECT
            CASE
                WHEN order_count > 1 THEN 'Repeat Customer'
                ELSE 'New Customer'
            END AS customer_type,
            COUNT(*) AS customer_count
        FROM customer_orders
        GROUP BY
            CASE
                WHEN order_count > 1 THEN 'Repeat Customer'
                ELSE 'New Customer'
            END
        ORDER BY customer_count DESC;
    """
    return pd.read_sql(query, get_engine())



@st.cache_data(ttl=600)
def load_top_customers():
    query = """
        WITH customer_spending AS (
            SELECT
                c.customer_unique_id,
                COUNT(DISTINCT o.order_id) AS order_count,
                SUM(oi.price + oi.freight_value) AS total_spending
            FROM customers AS c
            JOIN orders AS o
                ON c.customer_id = o.customer_id
            JOIN order_items AS oi
                ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY c.customer_unique_id
        )
        SELECT
            customer_unique_id,
            order_count,
            ROUND(total_spending, 2) AS total_spending
        FROM customer_spending
        ORDER BY total_spending DESC
        LIMIT 10;
    """
    top_customers = pd.read_sql(query, get_engine())

    top_customers["customer_label"] = (
        top_customers["customer_unique_id"].str[:8] + "..."
    )
    return top_customers



@st.cache_data(ttl=600)
def load_delivery_metrics():
    query = """
        SELECT
            ROUND(
                AVG(
                    DATEDIFF(
                        order_delivered_customer_date,
                        order_purchase_timestamp
                    )
                ),
                2
            ) AS average_delivery_days,

            SUM(
                CASE
                    WHEN order_delivered_customer_date
                         <= order_estimated_delivery_date
                    THEN 1
                    ELSE 0
                END
            ) AS on_time_orders,

            SUM(
                CASE
                    WHEN order_delivered_customer_date
                         > order_estimated_delivery_date
                    THEN 1
                    ELSE 0
                END
            ) AS delayed_orders

        FROM orders
        WHERE order_status = 'delivered'
          AND order_delivered_customer_date IS NOT NULL
          AND order_estimated_delivery_date IS NOT NULL;
    """
    return pd.read_sql(query, get_engine())



@st.cache_data(ttl=600)
def load_delivery_status():
    query = """
        SELECT
            CASE
                WHEN order_delivered_customer_date
                     <= order_estimated_delivery_date
                THEN 'On Time'
                ELSE 'Delayed'
            END AS delivery_status,

            COUNT(*) AS order_count

        FROM orders
        WHERE order_status = 'delivered'
          AND order_delivered_customer_date IS NOT NULL
          AND order_estimated_delivery_date IS NOT NULL

        GROUP BY
            CASE
                WHEN order_delivered_customer_date
                     <= order_estimated_delivery_date
                THEN 'On Time'
                ELSE 'Delayed'
            END;
    """

    return pd.read_sql(query, get_engine())



@st.cache_data(ttl=600)
def load_delivery_vs_review_score():
    query = """
        WITH order_review_scores AS (
            SELECT
                order_id,
                AVG(review_score) AS review_score
            FROM reviews
            GROUP BY order_id
        ),

        delivery_performance AS (
            SELECT
                o.order_id,

                CASE
                    WHEN o.order_delivered_customer_date
                         <= o.order_estimated_delivery_date
                    THEN 'On Time'
                    ELSE 'Delayed'
                END AS delivery_status,

                r.review_score

            FROM orders AS o
            JOIN order_review_scores AS r
                ON o.order_id = r.order_id

            WHERE o.order_status = 'delivered'
              AND o.order_delivered_customer_date IS NOT NULL
              AND o.order_estimated_delivery_date IS NOT NULL
        )

        SELECT
            delivery_status,
            ROUND(AVG(review_score), 2) AS average_review_score,
            COUNT(*) AS reviewed_orders

        FROM delivery_performance

        GROUP BY delivery_status
        ORDER BY average_review_score DESC;
    """
    return pd.read_sql(query, get_engine())



@st.cache_data(ttl=600)
def load_review_score_distribution():
    query = """
        SELECT
            review_score,
            COUNT(*) AS review_count
        FROM reviews
        GROUP BY review_score
        ORDER BY review_score;
    """

    return pd.read_sql(query, get_engine())



@st.cache_data(ttl=600)
def load_reviews_by_category():
    query = """
        WITH order_review_scores AS (
            SELECT
                order_id,
                AVG(review_score) AS review_score
            FROM reviews
            GROUP BY order_id
        ),

        order_categories AS (
            SELECT DISTINCT
                oi.order_id,
                COALESCE(
                    ct.product_category_name_english,
                    p.product_category_name,
                    'Unknown'
                ) AS category
            FROM order_items AS oi
            JOIN products AS p
                ON oi.product_id = p.product_id
            LEFT JOIN category_translation AS ct
                ON p.product_category_name = ct.product_category_name
        )

        SELECT
            oc.category,
            ROUND(AVG(r.review_score), 2) AS average_review_score,
            COUNT(*) AS reviewed_orders

        FROM order_categories AS oc
        JOIN order_review_scores AS r
            ON oc.order_id = r.order_id

        GROUP BY oc.category
        HAVING COUNT(*) >= 50
        ORDER BY average_review_score ASC
        LIMIT 10;
    """
    return pd.read_sql(query, get_engine())

@st.cache_data(ttl=600)
def load_top_sellers():
    query = """
        SELECT
            oi.seller_id,
            COUNT(DISTINCT oi.order_id) AS seller_order_count,
            COUNT(*) AS items_sold,
            ROUND(SUM(oi.price), 2) AS product_revenue,
            ROUND(SUM(oi.freight_value), 2) AS freight_value,
            ROUND(
                SUM(oi.price + oi.freight_value),
                2
            ) AS gross_order_value
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY oi.seller_id
        ORDER BY product_revenue DESC
        LIMIT 10;
    """

    top_sellers = pd.read_sql(
        query,
        get_engine()
    )

    top_sellers["seller_label"] = (
        top_sellers["seller_id"].str[:8] + "..."
    )

    return top_sellers



st.title("Cart2Insights Business Intelligence Dashboard")
st.markdown("Interactive analysis of e-commerce sales, customers, sellers, delivery, and reviews.")
st.caption("Gross order value = product price + freight value for delivered orders.")

st.sidebar.header("Navigation & Filters")
selected_page = st.sidebar.selectbox(
    "Choose dashboard page",
    [
        "Overview",
        "Sales Analysis",
        "Customer Analysis",
        "Seller & Product Analysis",
        "Delivery Analysis",
        "Customer Experience",
        "Insights & Recommendations"
    ]
)

if st.sidebar.button("Refresh dashboard data"):
    st.cache_data.clear()
    st.rerun()


if selected_page == "Overview":
    try:
        engine = get_engine()

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        st.success("MySQL database connected successfully!")

        with st.expander("View loaded database tables"):
            table_names = load_table_names()
            st.dataframe(
                table_names,
                use_container_width=True,
                hide_index=True
            )

        st.header("Business Overview")

        metrics = load_overview_metrics()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Delivered Orders",
                f"{int(metrics.loc[0, 'total_orders']):,}"
            )

        with col2:
            st.metric(
                "Gross Order Value",
                f"R$ {metrics.loc[0, 'total_gross_order_value']:,.2f}"
            )

        with col3:
            st.metric(
                "Average Gross Order Value",
                f"R$ {metrics.loc[0, 'average_gross_order_value']:,.2f}"
            )

        st.subheader("Monthly Gross Order Value Trend")

        monthly_revenue = load_monthly_revenue()

        month_options = monthly_revenue["month"].tolist()

        selected_months = st.sidebar.multiselect(
            "Select revenue months",
            options=month_options,
            default=month_options
        )

        filtered_monthly_revenue = monthly_revenue[
            monthly_revenue["month"].isin(selected_months)
        ].copy()

        if filtered_monthly_revenue.empty:
            st.warning("Select at least one month.")
        else:
            st.line_chart(
                filtered_monthly_revenue,
                x="month",
                y="gross_order_value",
                use_container_width=True
            )

            st.dataframe(
                filtered_monthly_revenue,
                use_container_width=True,
                hide_index=True
            )
        

        st.subheader("Top 10 Categories by Gross Order Value")

        top_categories = load_top_categories()

        category_options = top_categories["category"].tolist()
        selected_categories = st.sidebar.multiselect(
            "Select top categories",
            options=category_options,
            default=category_options
        )

        filtered_top_categories = top_categories[
            top_categories["category"].isin(selected_categories)
        ].copy()

        if filtered_top_categories.empty:
            st.warning("Select at least one product category.")
        else:
            st.bar_chart(
                filtered_top_categories,
                x="category",
                y="gross_order_value",
                use_container_width=True
            )

            st.dataframe(
                filtered_top_categories,
                use_container_width=True,
                hide_index=True
            )

    except Exception as error:
        st.error("Could not load the Overview dashboard.")
        st.exception(error)



elif selected_page == "Sales Analysis":
    st.header("Sales Analysis")

    try:
        sales_by_state = load_revenue_by_state()

        state_options = sales_by_state["state"].tolist()

        selected_states = st.sidebar.multiselect(
            "Select customer states",
            options=state_options,
            default=state_options
        )

        filtered_sales_by_state = sales_by_state[
            sales_by_state["state"].isin(selected_states)
        ].copy()
        

        st.subheader("Gross Order Value by Customer State")

        if filtered_sales_by_state.empty:
            st.warning("Select at least one customer state.")
        else:
            st.bar_chart(
                filtered_sales_by_state,
                x="state",
                y="gross_order_value",
                use_container_width=True
            )

            st.dataframe(
                filtered_sales_by_state,
                use_container_width=True,
                hide_index=True
            )

        st.subheader("Top 10 Products by Units Sold")

        top_products = load_top_products()

        st.bar_chart(
            top_products,
            x="product_label",
            y="units_sold",
            use_container_width=True
        )

        st.dataframe(
            top_products[
                ["product_id", "units_sold", "gross_order_value"]
            ],
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error("Could not load Sales Analysis.")
        st.exception(error)



elif selected_page == "Customer Analysis":
    st.header("Customer Analysis")

    try:
        customer_types = load_customer_type_counts()

        st.subheader("New vs Repeat Customers")

        st.bar_chart(
            customer_types,
            x="customer_type",
            y="customer_count",
            use_container_width=True
        )

        st.dataframe(
            customer_types,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Top 10 Customers by Total Spending")

        top_customers = load_top_customers()

        st.bar_chart(
            top_customers,
            x="customer_label",
            y="total_spending",
            use_container_width=True
        )

        st.dataframe(
            top_customers[
                ["customer_unique_id", "order_count", "total_spending"]
            ],
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error("Could not load Customer Analysis.")
        st.exception(error)



elif selected_page == "Seller & Product Analysis":
    st.header("Seller & Product Analysis")

    try:
        st.subheader("Top 10 Sellers by Product Revenue")

        top_sellers = load_top_sellers()

        st.bar_chart(
            top_sellers,
            x="seller_label",
            y="product_revenue",
            use_container_width=True
        )

        st.dataframe(
            top_sellers[
                [
                    "seller_id",
                    "seller_order_count",
                    "items_sold",
                    "product_revenue",
                    "freight_value",
                    "gross_order_value"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Top 10 Products by Units Sold")

        top_products = load_top_products()

        st.bar_chart(
            top_products,
            x="product_label",
            y="units_sold",
            use_container_width=True
        )

        st.dataframe(
            top_products,
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error(
            "Could not load Seller & Product Analysis."
        )
        st.exception(error)



elif selected_page == "Delivery Analysis":
    st.header("Delivery Analysis")

    try:
        delivery_metrics = load_delivery_metrics()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Average Delivery Time",
                f"{delivery_metrics.loc[0, 'average_delivery_days']:.2f} days"
            )

        with col2:
            st.metric(
                "On-Time Deliveries",
                f"{int(delivery_metrics.loc[0, 'on_time_orders']):,}"
            )

        with col3:
            st.metric(
                "Delayed Deliveries",
                f"{int(delivery_metrics.loc[0, 'delayed_orders']):,}"
            )

        st.subheader("On-Time vs Delayed Orders")

        delivery_status = load_delivery_status()

        st.bar_chart(
            delivery_status,
            x="delivery_status",
            y="order_count",
            use_container_width=True
        )

        st.dataframe(
            delivery_status,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Delivery Performance vs Customer Review Score")

        delivery_reviews = load_delivery_vs_review_score()

        st.bar_chart(
            delivery_reviews,
            x="delivery_status",
            y="average_review_score",
            use_container_width=True
        )

        st.dataframe(
            delivery_reviews,
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error("Could not load Delivery Analysis.")
        st.exception(error)



elif selected_page == "Customer Experience":
    st.header("Customer Experience")

    try:
        review_distribution = load_review_score_distribution()

        total_reviews = review_distribution["review_count"].sum()

        average_review_score = (
            review_distribution["review_score"]
            .mul(review_distribution["review_count"])
            .sum()
            / total_reviews
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Average Review Score",
                f"{average_review_score:.2f} / 5"
            )

        with col2:
            st.metric(
                "Total Reviews",
                f"{int(total_reviews):,}"
            )

        st.subheader("Review Score Distribution")

        st.bar_chart(
            review_distribution,
            x="review_score",
            y="review_count",
            use_container_width=True
        )

        st.dataframe(
            review_distribution,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Categories with Lowest Average Review Score")

        reviews_by_category = load_reviews_by_category()

        st.bar_chart(
            reviews_by_category,
            x="category",
            y="average_review_score",
            use_container_width=True
        )

        st.dataframe(
            reviews_by_category,
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error("Could not load Customer Experience data.")
        st.exception(error)



elif selected_page == "Insights & Recommendations":
    st.header("Business Insights & Recommendations")

    try:
        delivery_reviews = load_delivery_vs_review_score()
        customer_types = load_customer_type_counts()
        top_categories = load_top_categories()
        monthly_gov = load_monthly_revenue()

        review_scores = delivery_reviews.set_index("delivery_status")
        on_time_score = review_scores.loc[
            "On Time",
            "average_review_score"
        ]
        delayed_score = review_scores.loc[
            "Delayed",
            "average_review_score"
        ]
        review_gap = on_time_score - delayed_score

        repeat_customers = customer_types.loc[
            customer_types["customer_type"] == "Repeat Customer",
            "customer_count"
        ].sum()
        total_customers = customer_types["customer_count"].sum()
        repeat_rate = repeat_customers / total_customers * 100

        top_category = top_categories.iloc[0]
        peak_month = monthly_gov.loc[
            monthly_gov["gross_order_value"].idxmax()
        ]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Top Category",
                top_category["category"],
                f"R$ {top_category['gross_order_value']:,.2f}"
            )

        with col2:
            st.metric(
                "Peak Month",
                peak_month["month"],
                f"R$ {peak_month['gross_order_value']:,.2f}"
            )

        with col3:
            st.metric(
                "Repeat Customer Rate",
                f"{repeat_rate:.2f}%"
            )

        with col4:
            st.metric(
                "On-Time Review Advantage",
                f"{review_gap:.2f} points"
            )

        st.subheader("Key Findings")
        st.markdown(
            f"""
- On-time deliveries received an average review score of
  **{on_time_score:.2f}**, compared with **{delayed_score:.2f}**
  for delayed deliveries.
- Delivery days and review score had a correlation of **-0.33**,
  indicating that longer delivery times are associated with lower
  customer satisfaction.
- Only **{repeat_rate:.2f}%** of delivered-order customers made
  more than one purchase.
- **{top_category['category']}** generated the highest category
  gross order value.
- **{peak_month['month']}** recorded the highest monthly gross
  order value.
"""
        )

        st.subheader("Business Recommendations")
        st.markdown(
            """
1. **Reduce delivery delays:** Track delay-prone states, sellers,
   and carriers, and create alerts before estimated delivery dates
   are missed.

2. **Improve customer retention:** Use post-delivery campaigns,
   loyalty rewards, and targeted offers because the repeat-customer
   rate is very low.

3. **Protect customer experience:** Monitor delivery performance
   together with review scores because delayed orders receive
   substantially lower ratings.

4. **Support high-performing categories:** Maintain inventory and
   seller capacity for leading categories while avoiding excessive
   dependence on one category.

5. **Do not over-prioritize payment method:** The payment-method
   association with order status was statistically significant but
   extremely weak (Cramer's V = 0.0393).
"""
        )

        st.subheader("Statistical Evidence")
        evidence = pd.DataFrame(
            {
                "Test": [
                    "Welch's t-test",
                    "One-way ANOVA",
                    "Chi-square test"
                ],
                "Business question": [
                    "Do review scores differ by delivery status?",
                    "Does spending differ across categories?",
                    "Is payment method associated with order status?"
                ],
                "Result": [
                    "Significant; on-time reviews are higher",
                    "Significant category spending differences",
                    "Significant but extremely weak association"
                ]
            }
        )
        st.dataframe(
            evidence,
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error(
            "Could not load business insights and recommendations."
        )
        st.exception(error)

