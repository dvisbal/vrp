# vrp_solution.py
#
# Run with: 
# python3. vrp_solution.py problem_file.txt
#
# tested with python 3.10.12

import argparse
import math

parser = argparse.ArgumentParser()
vrp_file_path = parser.add_argument("vrp_file_path")
args = parser.parse_args()

euclidean_distance_cache = {}
def euclidean_distance(x1, y1, x2, y2):
    if ( (x1, x2), (y1, y2) ) in euclidean_distance_cache:
        return euclidean_distance_cache[( (x1, x2), (y1, y2) )]
    elif ( (y1, y2),(x1, x2) ) in euclidean_distance_cache:
        return euclidean_distance_cache[(y1, y2),(x1, x2)]

    distance = math.sqrt( (x2 - x1)**2 + (y2 - y1)**2  )
    euclidean_distance_cache[( (x1, x2), (y1, y2) )] = distance
    return distance

loads = []
drivers = []

# parse the vrp file into a list of dict objects representing each load
with open(args.vrp_file_path) as vrp_file:
    is_first_line = True
    for line in vrp_file:
        if is_first_line:
            is_first_line = False # skip the first line
        else:
            line_split_on_spaces = line.split()

            id = int(line_split_on_spaces[0])

            pickup_x_y = line_split_on_spaces[1].strip("()").split(",")
            pickup_x = float(pickup_x_y[0])
            pickup_y = float(pickup_x_y[1])
            
            dropoff_x_y = line_split_on_spaces[2].strip("()").split(",")
            dropoff_x = float(dropoff_x_y[0])
            dropoff_y = float(dropoff_x_y[1])

            # calc times/cost for common paths the drivers will take
            time_from_depot_to_pickup_point = euclidean_distance(0, 0, pickup_x, pickup_y)
            time_from_dropoff_point_to_depot = euclidean_distance(dropoff_x, dropoff_y, 0, 0)
            time_to_deliver = euclidean_distance(pickup_x, pickup_y, dropoff_x, dropoff_y)
            time_to_deliver_plus_time_back_to_depot = time_to_deliver + time_from_depot_to_pickup_point            
            
            loads.append({
                "id": id,
                "pickup": {"x": pickup_x, "y": pickup_y},
                "dropoff": {"x": dropoff_x, "y": dropoff_y},
                "time_from_depot_to_pickup_point": time_from_depot_to_pickup_point,
                "time_from_dropoff_point_to_depot": time_from_dropoff_point_to_depot,
                "time_to_deliver": time_to_deliver,
                "time_to_deliver_plus_time_back_to_depot": time_to_deliver_plus_time_back_to_depot
            })

# find the max shift time that can be utilized given the time left in the shift
#
# searches loads that could be taken from last_loads's dropoff point
# and returns a path that utilizes the most shift time while the driver can still
# get back to the depot without going over their shift time
def find_max_shift_time_path(time_left_in_shift, unclaimed_loads, last_load, potential_next_load):
    time_to_potential_next_pickup_point = euclidean_distance(
        last_load['dropoff']['x'],
        last_load['dropoff']['y'],
        potential_next_load['pickup']['x'],
        potential_next_load['pickup']['y']
    )

    time_to_potential_next_dropoff_point = time_to_potential_next_pickup_point + \
        potential_next_load['time_to_deliver']
    
    time_back_to_depot = time_to_potential_next_dropoff_point + potential_next_load['time_from_dropoff_point_to_depot']

    if time_back_to_depot > time_left_in_shift:
        return -1, []

    min_time_left_in_shift_if_taking_this_load_found = -1
    path_with_min_shift_time_left_to_get_back_to_depot_found = []

    for l in unclaimed_loads:
        unclaimed_loads_without_potential_next_load = [_l for _l in unclaimed_loads if _l['id'] != potential_next_load['id']]
        unclaimed_loads_without_potential_next_load = unclaimed_loads_without_potential_next_load[:min(int(len(unclaimed_loads_without_potential_next_load)/10), 3)]
        if l['id'] != potential_next_load['id']:
            min_time_left_in_shift_if_taking_this_load, path_with_min_shift_time_left_to_get_back_to_depot = find_max_shift_time_path(
                time_left_in_shift - time_to_potential_next_dropoff_point, 
                unclaimed_loads_without_potential_next_load, 
                potential_next_load, 
                l
            )
            if min_time_left_in_shift_if_taking_this_load != -1 and (min_time_left_in_shift_if_taking_this_load < min_time_left_in_shift_if_taking_this_load_found or min_time_left_in_shift_if_taking_this_load_found == -1):
                min_time_left_in_shift_if_taking_this_load_found = min_time_left_in_shift_if_taking_this_load
                path_with_min_shift_time_left_to_get_back_to_depot_found = path_with_min_shift_time_left_to_get_back_to_depot

    if potential_next_load['id'] == 1:
        a = 1

    if min_time_left_in_shift_if_taking_this_load_found == -1:
        # if we get here then there are no further loads after potential next node that the driver has time for
        min_time_left_in_shift_if_taking_this_load_found = time_left_in_shift - time_to_potential_next_dropoff_point

    return min_time_left_in_shift_if_taking_this_load_found, [potential_next_load] + path_with_min_shift_time_left_to_get_back_to_depot_found

##############################
#
#   Assign loads to drivers
#
##############################

# sort loads by pickup point with min time to depot
loads.sort(key = lambda load: load['time_from_depot_to_pickup_point'])

# loop until all loads have a driver:
#   1. new driver
#   2. get closest pickup point
#   3. give driver the load and re-calc time left in shift
#   4. For each unclaimed load:
#       use recursion to check if there is a path the 
#       driver has time to take that uses the most 
#       amount of time left in the driver shift
while len(loads) > 0:
    # give driver their first load
    # pick the load that has the closest pickup point to the depot
    last_load_given_to_driver = loads.pop()
    drivers.append([last_load_given_to_driver['id']])

    # calc time left in driver's shift after taking load
    time_left_in_shift = 12*60
    time_left_in_shift -= last_load_given_to_driver['time_from_depot_to_pickup_point'] + last_load_given_to_driver['time_to_deliver']
    # time_back_to_depot_from_last_dropoff_point = last_load_given_to_driver['time_from_dropoff_point_to_depot']

    # keep giving the new driver loads as long as there is still time 
    # to get back to the depot before the driver's shift ends
    if len(loads) > 0:
        # time_left_in_shift_at_last_dropoff_point = time_left_in_shift - time_back_to_depot_from_last_dropoff_point

        min_shift_time_left = -1
        min_shift_time_left_path = []

        for l in loads:
            min_time, min_time_path = find_max_shift_time_path(time_left_in_shift, loads, last_load_given_to_driver, l)
            if min_time != -1 and (min_time < min_shift_time_left or min_shift_time_left == -1):
                min_shift_time_left = min_time
                min_shift_time_left_path = min_time_path
        
        load_ids_driver_is_taking = []
        if min_shift_time_left != -1:
            load_ids_driver_is_taking = [l['id'] for l in min_shift_time_left_path]
            drivers[-1] += load_ids_driver_is_taking
            
            # remove all the loads given to the new driver
            loads = [l for l in loads if l['id'] not in load_ids_driver_is_taking]

for driver in drivers:
    print(f"{driver}")




