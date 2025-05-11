#include "osrm/osrm.hpp"
#include "osrm/engine_config.hpp"
#include "osrm/route_parameters.hpp"
#include <fstream>
#include <iostream>
#include <vector>
#include <string>
#include <sstream>

/*
Compilation:
g++ -std=c++14 calculate_distances.cpp -o calculate_distances -I/usr/local/include/osrm -L/usr/local/lib -losrm -lboost_system -lboost_filesystem -lboost_iostreams -lboost_thread
*/

int main(int argc, char* argv[]) {
    std::string csv_file_path = "coordinates.csv"; // Default CSV file path
    std::string out_file_path = "distances.csv"; // Default out file path
    int max_lines = -1; // Default to read all lines
    if (argc > 1) csv_file_path = argv[1];
    if (argc > 2) out_file_path = argv[2];
    if (argc > 3) max_lines = std::stoi(argv[3]);

    std::ifstream file(csv_file_path);
    if (!file.is_open()) {
        std::cerr << "Failed to open file: " << csv_file_path << std::endl;
        return 1;
    }

    osrm::EngineConfig config;
    config.storage_config = {"/home/igreenberg/code/osrm/data/sudeste-latest.osrm"};
    config.use_shared_memory = false;
    config.algorithm = osrm::EngineConfig::Algorithm::MLD;
    const osrm::OSRM osrm{config};

    std::vector<std::pair<double, double>> coordinates;
    std::string line;
    getline(file, line); // Skip header
    int line_count = 0;
    while (getline(file, line) && (max_lines == -1 || line_count < max_lines)) {
        std::stringstream linestream(line);
        std::string value;
        double lat, lon;
        int column_index = 0;
        while (getline(linestream, value, ',')) {
            if (column_index == 8) lat = std::stod(value); // Assume 2nd column is latitude
            if (column_index == 9) {
                lon = std::stod(value); // Assume 3rd column is longitude
                coordinates.push_back({lon, lat});
                break;
            }
            column_index++;
        }
        line_count++;
    }
    file.close();

    std::ofstream output_file(out_file_path);
    output_file << "origin" << "," << "destination" << "," << "distance" << "," << "duration" << std::endl;
    for (size_t i = 0; i < coordinates.size(); ++i) {
        for (size_t j = 0; j < coordinates.size(); ++j) {
            osrm::RouteParameters params;
            params.coordinates.push_back(osrm::util::Coordinate(osrm::util::FloatLongitude{coordinates[i].first}, osrm::util::FloatLatitude{coordinates[i].second}));
            params.coordinates.push_back(osrm::util::Coordinate(osrm::util::FloatLongitude{coordinates[j].first}, osrm::util::FloatLatitude{coordinates[j].second}));

            osrm::json::Object result;
            const auto status = osrm.Route(params, result);

            if (status == osrm::Status::Ok) {
               auto &routes = result.values["routes"].get<osrm::json::Array>();
               auto &route = routes.values.at(0).get<osrm::json::Object>();
               auto distance = route.values["distance"].get<osrm::json::Number>().value; // Distance in meters
               auto duration = route.values["duration"].get<osrm::json::Number>().value; // Duration in seconds

               output_file << i << "," << j << "," << distance << "," << duration << std::endl;
            } else {
               output_file << i << "," << j << ", error, error" << std::endl;
            }
        }
    }
    output_file.close();
    return 0;
}

