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
g++ -std=c++14 calculate_cross_distances.cpp -o calculate_cross_distances -I/usr/local/include/osrm -L/usr/local/lib -losrm -lboost_system -lboost_filesystem -lboost_iostreams -lboost_thread
*/

int main(int argc, char* argv[]) {
    std::string csv_file_path1 = "coordinates1.csv"; // Default CSV file path
    std::string csv_file_path2 = "coordinates2.csv"; // Default CSV file path
    std::string out_file_path = "cross_distances.csv"; // Default out file path
    int max_lines = -1; // Default to read all lines
    if (argc > 1) csv_file_path1 = argv[1];
    if (argc > 2) csv_file_path2 = argv[2];
    if (argc > 3) out_file_path = argv[3];
    if (argc > 4) max_lines = std::stoi(argv[4]);

    std::ifstream file1(csv_file_path1);
    if (!file1.is_open()) {
        std::cerr << "Failed to open file: " << csv_file_path1 << std::endl;
        return 1;
    }

    std::ifstream file2(csv_file_path2);
    if (!file2.is_open()) {
        std::cerr << "Failed to open file: " << csv_file_path2 << std::endl;
        return 1;
    }

    osrm::EngineConfig config;
    config.storage_config = {"/home/igreenberg/code/osrm/data/sudeste-latest.osrm"};
    config.use_shared_memory = false;
    config.algorithm = osrm::EngineConfig::Algorithm::MLD;
    const osrm::OSRM osrm{config};

    std::vector<std::pair<double, double>> coordinates1;
    std::string line;
    getline(file1, line); // Skip header
    int line_count = 0;
    while (getline(file1, line) && (max_lines == -1 || line_count < max_lines)) {
        std::stringstream linestream(line);
        std::string value;
        double lat, lon;
        int column_index = 0;
        while (getline(linestream, value, ',')) {
            if (column_index == 9) lat = std::stod(value);
            if (column_index == 10) {
                lon = std::stod(value);
                coordinates1.push_back({lon, lat});
                //std::cout << lon << "," << lat << std::endl;
                break;
            }
            column_index++;
        }
        line_count++;
    }
    file1.close();

    std::vector<std::pair<double, double>> coordinates2;
    getline(file2, line); // Skip header
    line_count = 0;
    while (getline(file2, line) && (max_lines == -1 || line_count < max_lines)) {
        std::stringstream linestream(line);
        std::string value;
        double lat, lon;
        int column_index = 0;
        while (getline(linestream, value, ',')) {
            if (column_index == 7) lat = std::stod(value);
            if (column_index == 8) {
                lon = std::stod(value);
                coordinates2.push_back({lon, lat});
                //std::cout << lon << "," << lat << std::endl;
                break;
            }
            column_index++;
        }
        line_count++;
    }
    file2.close();
    
    std::stringstream buffer;
    buffer << "direction" << "," << "depot" << "," << "customer" << "," << "distance" << "," << "duration" << std::endl;

    for (size_t i = 0; i < coordinates1.size(); ++i) {
        for (size_t j = 0; j < coordinates2.size(); ++j) {
            osrm::RouteParameters params;
            params.coordinates.push_back(osrm::util::Coordinate(osrm::util::FloatLongitude{coordinates1[i].first}, osrm::util::FloatLatitude{coordinates1[i].second}));
            params.coordinates.push_back(osrm::util::Coordinate(osrm::util::FloatLongitude{coordinates2[j].first}, osrm::util::FloatLatitude{coordinates2[j].second}));

            osrm::json::Object result;
            const auto status = osrm.Route(params, result);

            if (status == osrm::Status::Ok) {
               auto &routes = result.values["routes"].get<osrm::json::Array>();
               auto &route = routes.values.at(0).get<osrm::json::Object>();
               auto distance = route.values["distance"].get<osrm::json::Number>().value; // Distance in meters
               auto duration = route.values["duration"].get<osrm::json::Number>().value; // Duration in seconds

               buffer << "from_depot," << i << "," << j << "," << distance << "," << duration << std::endl;
            } else {
               buffer << "from_depot," << i << "," << j << ", error, error" << std::endl;
            }
        }
    }
    
    for (size_t i = 0; i < coordinates2.size(); ++i) {
        for (size_t j = 0; j < coordinates1.size(); ++j) {
            osrm::RouteParameters params;
            params.coordinates.push_back(osrm::util::Coordinate(osrm::util::FloatLongitude{coordinates2[i].first}, osrm::util::FloatLatitude{coordinates2[i].second}));
            params.coordinates.push_back(osrm::util::Coordinate(osrm::util::FloatLongitude{coordinates1[j].first}, osrm::util::FloatLatitude{coordinates1[j].second}));

            osrm::json::Object result;
            const auto status = osrm.Route(params, result);

            if (status == osrm::Status::Ok) {
               auto &routes = result.values["routes"].get<osrm::json::Array>();
               auto &route = routes.values.at(0).get<osrm::json::Object>();
               auto distance = route.values["distance"].get<osrm::json::Number>().value; // Distance in meters
               auto duration = route.values["duration"].get<osrm::json::Number>().value; // Duration in seconds

               buffer << "to_depot," << j << "," << i << "," << distance << "," << duration << std::endl;
            } else {
               buffer << "to_depot," << j << "," << i << ", error, error" << std::endl;
            }
        }
    }
    
    std::ofstream output_file(out_file_path);
    output_file << buffer.str();
    output_file.close();
    return 0;
}

