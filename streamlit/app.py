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




st.title("Cart2Insights Business Info Dashboard")
st.markdown("An interactive dashboard for analysing e-commerce performance")
st.sidebar.header("Filters")
selected_page=st.sidebar.selectbox(
    "Choose dashboard page",
    ["Overview","Sale Analysis","Customer","Delivery Analysis"]
)


try:
    engine=get_engine()

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    st.success("Mysql database connected successfully")

    st.subheader("Available Database Tables")
    table_names = load_table_names()
    st.dataframe(table_names, use_container_width=True)


    st.subheader("Business Overview")
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
            f"Rs. {metrics.loc[0, 'total_revenue']:,.2f}"
        )
    with col3:
        st.metric(
            "Average Order Value",
            f"Rs. {metrics.loc[0, 'average_order_value']:,.2f}"
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
    st.error("Could not connect to MySQL")
    st.exception(error)

st.subheader(selected_page)
