## Olist dataset processor

To generate locations for customers and depots (sellers), we used `main_generate_orders_coordinates()` in `brasilian_data_processing.py`. This relies on the [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

To calculate costs (driving durations), we used `calculate_distances.cpp` (for customer-customer driving durations) and `calculate_cross_distances.cpp` (for customer-depot driving durations). Both rely on the [OSRM package](https://github.com/Project-OSRM/osrm-backend).
