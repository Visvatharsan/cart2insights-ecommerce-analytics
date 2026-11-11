# Cart2Insights Entity-Relationship Diagram

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--|{ ORDER_ITEMS : contains
    PRODUCTS ||--o{ ORDER_ITEMS : appears_in
    SELLERS ||--o{ ORDER_ITEMS : fulfills
    ORDERS ||--o{ PAYMENTS : has
    ORDERS ||--o{ REVIEWS : receives
    CATEGORY_TRANSLATION ||--o{ PRODUCTS : translates
    GEOLOCATION }o..o{ CUSTOMERS : "postal prefix"
    GEOLOCATION }o..o{ SELLERS : "postal prefix"

    CUSTOMERS {
        char customer_id PK
        char customer_unique_id
        char customer_zip_code_prefix
        varchar customer_city
        char customer_state
    }

    ORDERS {
        char order_id PK
        char customer_id FK
        varchar order_status
        datetime order_purchase_timestamp
        datetime order_approved_at
        datetime order_delivered_carrier_date
        datetime order_delivered_customer_date
        datetime order_estimated_delivery_date
    }

    ORDER_ITEMS {
        char order_id PK,FK
        int order_item_id PK
        char product_id FK
        char seller_id FK
        datetime shipping_limit_date
        decimal price
        decimal freight_value
    }

    PRODUCTS {
        char product_id PK
        varchar product_category_name
        int product_name_length
        int product_description_length
        int product_photos_qty
        decimal product_weight_g
        decimal product_length_cm
        decimal product_height_cm
        decimal product_width_cm
    }

    SELLERS {
        char seller_id PK
        char seller_zip_code_prefix
        varchar seller_city
        char seller_state
    }

    PAYMENTS {
        char order_id PK,FK
        int payment_sequential PK
        varchar payment_type
        int payment_installments
        decimal payment_value
    }

    REVIEWS {
        char review_id PK
        char order_id PK,FK
        int review_score
        varchar review_comment_title
        text review_comment_message
        datetime review_creation_date
        datetime review_answer_timestamp
    }

    CATEGORY_TRANSLATION {
        varchar product_category_name PK
        varchar product_category_name_english
    }

    GEOLOCATION {
        bigint geolocation_id PK
        char geolocation_zip_code_prefix
        decimal geolocation_lat
        decimal geolocation_lng
        varchar geolocation_city
        char geolocation_state
    }
```

## Relationship notes

- `customer_id` identifies a customer record associated with an order, while `customer_unique_id` identifies the same buyer across different orders.
- `order_items` uses the composite primary key `(order_id, order_item_id)`.
- `payments` uses `(order_id, payment_sequential)` because an order can have multiple payment records.
- `reviews` uses `(review_id, order_id)` in this project schema.
- Geolocation joins are logical rather than enforced foreign keys because a postal-code prefix can have multiple coordinate records.
- Category translation is a lookup relationship. Products with missing categories are represented as `unknown`.
