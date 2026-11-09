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



st.title("Cart2Insights Business Info Dashboard")
st.markdown("An interactive dashboard for analysing e-commerce performance")
st.sidebar.header("Filters")
selected_page = st.sidebar.selectbox(
    "Choose dashboard page",
    [
        "Overview",
        "Sales Analysis",
        "Customer Analysis",
        "Delivery Analysis"
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
    st.info("Customer analysis charts will be added later.")


elif selected_page == "Delivery Analysis":
    st.header("Delivery Analysis")
    st.info("Delivery analysis charts will be added later.")