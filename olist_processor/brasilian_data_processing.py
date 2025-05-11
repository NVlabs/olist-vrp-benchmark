'''
Based on the "Brazilian E-Commerce Public Dataset by Olist":
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
'''

import numpy as np
import pandas as pd

BASE_PATH = r'/home/igreenberg/code/osrm/data/brasil_e_commerce_dataset'
PATH_ORDERS = f'{BASE_PATH}/olist_orders_dataset.csv'
PATH_ITEMS = f'{BASE_PATH}/olist_order_items_dataset.csv'
PATH_PRODUCTS = f'{BASE_PATH}/olist_products_dataset.csv'
PATH_CUSTOMERS = f'{BASE_PATH}/olist_customers_dataset.csv'
PATH_SELLERS = f'{BASE_PATH}/olist_sellers_dataset.csv'
PATH_GEO = f'{BASE_PATH}/olist_geolocation_dataset.csv'
START_DATE = '2017-02-15 00:00:00'
MAX_DAYS = 540

# https://www.latlong.net/place/rio-de-janeiro-brazil-27580.html
RIO_DE_JANEIRO = (-22.908333, -43.196388)
SAO_PAULO = (-23.533773, -46.625290)
BRASILIA = (-15.793889, -47.882778)


def get_locations_around(gg, center=RIO_DE_JANEIRO, diameter=100e3):
    # calculate x/y distances from the center
    gg['y'] = 110574 * (gg.geolocation_lat - center[0])
    gg['x'] = 111320 * (gg.geolocation_lng - center[1]) * np.cos(np.deg2rad(center[0]))
    gg['Linf_from_center'] = np.maximum(gg['x'].abs(), gg['y'].abs())
    gg = gg[gg['Linf_from_center'] <= diameter / 2]
    return gg

def get_data_in_dates(dd, start_date=START_DATE, n_days=MAX_DAYS):
    dt = (pd.to_datetime(dd.order_estimated_delivery_date) - pd.to_datetime(start_date)).dt
    dd['day'] = dt.total_seconds() / (24 * 3600)
    dd = dd[(dd.day>=0) & (dd.day<=n_days)]
    return dd

def get_orders_geo_data(path_orders=PATH_ORDERS, path_customers=PATH_CUSTOMERS, merge_col='customer_id',
                        zip_col='customer_zip_code_prefix', zip2loc='rand', filter_dates=True, drop_dup=None):
    # orders
    oo = pd.read_csv(path_orders)
    if drop_dup:
        oo.drop_duplicates(drop_dup, keep='first', inplace=True)
    cc = pd.read_csv(path_customers)
    dd = pd.merge(oo, cc, on=merge_col)
    if filter_dates:
        dd = get_data_in_dates(dd)
    dd.reset_index(drop=True, inplace=True)

    # order volume
    pp = pd.read_csv(PATH_PRODUCTS)
    pp['volume_liter'] = pp.product_length_cm * pp.product_height_cm * pp.product_width_cm / 1000
    items = pd.read_csv(PATH_ITEMS)
    items = items.merge(pp[['product_id', 'volume_liter']], on='product_id', how='left')
    vol_per_order = items.groupby('order_id').apply(lambda d: d.volume_liter.sum())
    median_volume = vol_per_order.median()
    dd['volume_raw'] = dd.order_id.map(vol_per_order)
    dd['volume_clipped'] = dd['volume_raw'].fillna(median_volume).clip(0, 100)

    # geo data
    gg = pd.read_csv(PATH_GEO)
    gg[zip_col] = gg['geolocation_zip_code_prefix']
    if zip2loc == 'first':
        gg.drop_duplicates(subset=zip_col, keep='first', inplace=True)
        dd = pd.merge(dd, gg, on=zip_col)
    elif zip2loc == 'rand':
        def get_random_locations(d):
            zip = d[zip_col].values[0]
            g = gg[gg[zip_col] == zip]
            if len(g) == 0:
                return pd.DataFrame()
            d['geolocation_lat'] = np.random.choice(g.geolocation_lat, len(d), replace=True)
            d['geolocation_lng'] = np.random.choice(g.geolocation_lng, len(d), replace=True)
            return d
        dd = dd.groupby(zip_col).apply(get_random_locations)
    else:
        raise ValueError(zip2loc)

    # filter cols
    if filter_dates:
        cols = ['order_id', 'order_estimated_delivery_date', 'day', 'customer_id', 'customer_zip_code_prefix',
                'customer_city', 'customer_state', 'geolocation_lat', 'geolocation_lng']
        dd = dd[cols]
        dd.sort_values('day', inplace=True)
    if 'seller_city' in dd.columns:
        dd.drop(['seller_city'], axis=1, inplace=True)
    dd.reset_index(drop=True, inplace=True)

    return dd


def main_generate_orders_coordinates(cities_map=None, load_kwargs=None, base_path=BASE_PATH,
                                     save_name='coordinates'):
    if cities_map is None:
        cities_map = dict(rio=RIO_DE_JANEIRO, sao_paulo=SAO_PAULO, brasilia=BRASILIA)
    if load_kwargs is None:
        load_kwargs = {}

    dd = get_orders_geo_data(**load_kwargs)

    if save_name:
        dd.to_csv(f'{base_path}/{save_name}_all.csv', index=False)
    for k, center in cities_map.items():
        gg = get_locations_around(dd.copy(), center=center, diameter=100e3)
        if save_name:
            gg.to_csv(f'{base_path}/{save_name}_{k}.csv', index=False)
        gg['loc_id'] = [f'{x}_{y}' for x, y in zip(gg.geolocation_lat, gg.geolocation_lng)]
        print(k, gg.shape, gg.loc_id.nunique())


def generate_distance_matrix(dd, val='duration', is_full_and_sorted=True,
                             fill_errors_symm=True, save_to=None):
    if is_full_and_sorted:
        n = np.sqrt(len(dd))
        assert n % 1 == 0
        n = int(n)
        D = dd[val].values.reshape((n, n))
    else:
        max_i = dd.origin.max()
        max_j = dd.destination.max()
        matrix_shape = (max_i + 1, max_j + 1)
        D = np.zeros(matrix_shape)
        for i in range(len(dd)):
            D[dd.origin.values[i], dd.destination.values[i]] = dd[val].values[i]

    if fill_errors_symm:
        for i in range(D.shape[0]):
            for j in range(D.shape[1]):
                if D[i,j] == ' error':
                    if D[j,i] != ' error':
                        D[i, j] = D[j, i]
                    else:
                        D[i, j] = 0

    D = D.astype(float)

    if save_to:
        np.save(save_to, D)

    return D

def generate_cross_distances(dd, val='duration', fill_errors_symm=True, save_to=None):
    n_depots = dd.depot.max() + 1
    n_customers = dd.customer.max() + 1

    from_depot = np.zeros((n_depots, n_customers))
    d = dd[dd.direction=='from_depot']
    for i in range(len(d)):
        from_depot[d.depot.values[i], d.customer.values[i]] = d[val].values[i]

    to_depot = np.zeros((n_customers, n_depots))
    d = dd[dd.direction=='to_depot']
    for i in range(len(d)):
        to_depot[d.customer.values[i], d.depot.values[i]] = d[val].values[i]

    if fill_errors_symm and np.any([x==' error' for x in from_depot.reshape(-1)]):
        raise NotImplementedError(np.sum([x==' error' for x in from_depot.reshape(-1)]))

    from_depot, to_depot = from_depot.astype(float), to_depot.astype(float)

    if save_to:
        np.savez(save_to, from_depot=from_depot, to_depot=to_depot)

    return from_depot, to_depot


if __name__ == '__main__':
    # Generate orders geo-data
    # main_generate_orders_coordinates()

    # Generate sellers geo-data
    main_generate_orders_coordinates(
        load_kwargs=dict(path_orders=f'{BASE_PATH}/olist_order_items_dataset.csv', path_customers=PATH_SELLERS,
                         merge_col='seller_id', zip_col='seller_zip_code_prefix', drop_dup='seller_id', filter_dates=False),
        save_name='')  # 'sellers')
