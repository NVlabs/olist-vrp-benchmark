import warnings

import numpy as np
import pandas as pd


def sample_problems(n_problems, n_nodes, real_data=None, capacity=160, drone_mode=False, round_to_milliliter=True,
                    area='sao_paulo', label='train', base_path=r'data'):
    if real_data is None:
        real_data = load_real_data(area, label, base_path)

    positions, distance_matrix, demands = sample_distance_matrix(
        real_data, n_problems, n_nodes, drone_mode)

    if capacity < demands.max().item():
        warnings.warn(f'Vehicle capacity is {capacity}, but some demands are larger, up to {demands.max().item()}.')
    capacities = capacity * np.ones(n_problems, dtype=demands.dtype)

    if round_to_milliliter:
        capacities = 1000 * capacities
        demands = np.ceil(1000 * demands)

    return positions, distance_matrix, demands, capacities


def load_real_data(area='sao_paulo', label='train', base_path=r'data'):
    # load distance matrices
    all_customer_distances = np.load(f'{base_path}/distances_{area}_{label}.npy')
    depots_distances = np.load(f'{base_path}/cross_distances_{area}_{label}.npz')
    # depots->customers & customers->depots
    from_depot, to_depot = depots_distances['from_depot'], depots_distances['to_depot']

    # load locations
    all_customers = pd.read_csv(f'{base_path}/coordinates_{area}_{label}.csv')
    all_xs = all_customers.x.values
    all_ys = all_customers.y.values
    all_demands = all_customers.volume_clipped.values
    all_depots = pd.read_csv(f'{base_path}/sellers_{area}.csv')
    all_depot_xs = all_depots.x.values
    all_depot_ys = all_depots.y.values

    return dict(all_customer_distances=all_customer_distances, all_xs=all_xs, all_ys=all_ys,
                from_depot=from_depot, to_depot=to_depot, all_depot_xs=all_depot_xs, all_depot_ys=all_depot_ys,
                all_demands=all_demands)


def sample_distance_matrix(real_data, n_problems, n_nodes, drone_mode=False):
    # fetch real data
    all_customer_distances = real_data['all_customer_distances']
    all_xs = real_data['all_xs']
    all_ys = real_data['all_ys']
    from_depot = real_data['from_depot']
    to_depot = real_data['to_depot']
    all_depot_xs = real_data['all_depot_xs']
    all_depot_ys = real_data['all_depot_ys']
    all_demands = real_data['all_demands']

    # sample depots and customers
    n_depot_candidats, n_customer_candidates = from_depot.shape
    depot_ids = np.random.randint(low=0, high=n_depot_candidats, size=(n_problems,))
    customers = np.random.randint(low=0, high=n_customer_candidates, size=(n_problems, n_nodes - 1))

    # fill positions
    depot_xs, depot_ys = all_depot_xs[depot_ids], all_depot_ys[depot_ids]
    cust_xs, cust_ys, cust_demands = all_xs[customers], all_ys[customers], all_demands[customers]
    xs = np.concatenate((np.expand_dims(depot_xs, axis=-1), cust_xs), axis=1)
    ys = np.concatenate((np.expand_dims(depot_ys, axis=-1), cust_ys), axis=1)
    demands = np.concatenate((np.zeros_like(np.expand_dims(depot_ys, axis=-1)), cust_demands), axis=1)
    positions = np.stack((xs, ys), axis=-1)

    # fill distance matrix
    if drone_mode:
        distance_matrix = np.linalg.norm(positions[:, np.newaxis, :] - positions[:, :, np.newaxis], axis=-1)
    else:
        D = np.zeros((n_problems, n_nodes, n_nodes))
        for prob in range(n_problems):
            D[prob, 0, 1:] = from_depot[depot_ids[prob], customers[prob]]
            D[prob, 1:, 0] = to_depot[customers[prob], depot_ids[prob]]
            ii, jj = np.meshgrid(customers[prob], customers[prob], indexing='ij')
            D[prob, 1:, 1:] = all_customer_distances[ii, jj]
        distance_matrix = D

    return positions, distance_matrix, demands
