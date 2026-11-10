import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
import pandas as pd



st.set_page_config(
    page_title="Cart2Insights",
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
            ROUND(SUM(order_value), 2) AS total_revenue,
            ROUND(AVG(order_value), 2) AS average_order_value
        FROM (
            SELECT
                o.order_id,
                SUM(oi.price + oi.freight_value) AS order_value
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
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
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
                p.product_category_name,
                'Unknown'
            ) AS category,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        JOIN products AS p
            ON oi.product_id = p.product_id
        WHERE o.order_status = 'delivered'
        GROUP BY p.product_category_name
        ORDER BY revenue DESC
        LIMIT 10;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_revenue_by_state():
    query = """
        SELECT
            c.customer_state AS state,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        JOIN customers AS c
            ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
        GROUP BY c.customer_state
        ORDER BY revenue DESC;
    """
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=600)
def load_top_products():
    query = """
        SELECT
            oi.product_id,
            COUNT(*) AS units_sold,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
        FROM orders AS o
        JOIN order_items AS oi
            ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY oi.product_id
        ORDER BY units_sold DESC, revenue DESC
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
                    p.product_category_name,
                    'Unknown'
                ) AS category
            FROM order_items AS oi
            JOIN products AS p
                ON oi.product_id = p.product_id
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



st.title("Cart2Insights Business Info Dashboard")
st.markdown("An interactive dashboard for analysing e-commerce performance")
st.sidebar.header("Filters")
selected_page = st.sidebar.selectbox(
    "Choose dashboard page",
    [
        "Overview",
        "Sales Analysis",
        "Customer Analysis",
        "Delivery Analysis",
        "Customer Experience"
    ]
)


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
                "Total Revenue",
                f"R$ {metrics.loc[0, 'total_revenue']:,.2f}"
            )

        with col3:
            st.metric(
                "Average Order Value",
                f"R$ {metrics.loc[0, 'average_order_value']:,.2f}"
            )

        st.subheader("Monthly Revenue Trend")

        monthly_revenue = load_monthly_revenue()

        st.line_chart(
            monthly_revenue,
            x="month",
            y="revenue",
            use_container_width=True
        )

        st.dataframe(
            monthly_revenue,
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Top 10 Product Categories by Revenue")

        top_categories = load_top_categories()

        st.bar_chart(
            top_categories,
            x="category",
            y="revenue",
            use_container_width=True
        )

        st.dataframe(
            top_categories,
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

        st.subheader("Revenue by Customer State")

        st.bar_chart(
            sales_by_state,
            x="state",
            y="revenue",
            use_container_width=True
        )

        st.dataframe(
            sales_by_state,
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
                ["product_id", "units_sold", "revenue"]
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