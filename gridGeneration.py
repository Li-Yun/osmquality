import json
import numpy as np
import sys, os, csv
from kd_tree import kdTree
from utility import Utility
import argparse
import ast

# Road counts
def road_count(in_road, in_grids, in_counts, out_folder, initial_bb):
    road_data = []
    road_counts_his = np.zeros(len(in_grids))
    # load the Geo-json file and ignore other files
    if os.path.splitext(in_road)[1] == '.geojson':
        # open geojson files
        with open(in_road, encoding='utf-8') as new_f:
            in_data = json.load(new_f)
        
        # process all geometries excluding the 1st one
        for index in range(len(in_data['features'])):
            # discard a feature without its feature property
            if len(in_data['features'][index]['properties']) != 0:
                road_data.append([in_data['features'][index]['geometry']['type'], in_data['features'][index]['geometry']['coordinates']])

        # calculate the number of counts within a grid giving the road data
        for index2 in range(len(road_data)):
            if road_data[index2][0] == 'LineString':
                np_array = np.array(road_data[index2][1])
                tmp_array = np.zeros(len(in_grids))

                # iterate through all grids
                for ind in range(len(in_grids)):
                    for coordinate_ind in range(np_array.shape[0]):
                        if in_grids[ind][3] == initial_bb[3] and in_grids[ind][2] == initial_bb[2]:
                            if (np_array[coordinate_ind, :][0] >= in_grids[ind][0] and np_array[coordinate_ind, :][0] <= in_grids[ind][2] and
                                np_array[coordinate_ind, :][1] >= in_grids[ind][1] and np_array[coordinate_ind, :][1] <= in_grids[ind][3]):
                                tmp_array[ind] += 1
                        elif in_grids[ind][3] == initial_bb[3] and in_grids[ind][2] != initial_bb[2]:
                            if (np_array[coordinate_ind, :][0] >= in_grids[ind][0] and np_array[coordinate_ind, :][0] < in_grids[ind][2] and
                                np_array[coordinate_ind, :][1] >= in_grids[ind][1] and np_array[coordinate_ind, :][1] <= in_grids[ind][3]):
                                tmp_array[ind] += 1
                        elif in_grids[ind][3] != initial_bb[3] and in_grids[ind][2] == initial_bb[2]:
                            if (np_array[coordinate_ind, :][0] >= in_grids[ind][0] and np_array[coordinate_ind, :][0] <= in_grids[ind][2] and
                                np_array[coordinate_ind, :][1] >= in_grids[ind][1] and np_array[coordinate_ind, :][1] < in_grids[ind][3]):
                                tmp_array[ind] += 1
                        elif in_grids[ind][3] != initial_bb[3] and in_grids[ind][2] != initial_bb[2]:
                            if (np_array[coordinate_ind, :][0] >= in_grids[ind][0] and np_array[coordinate_ind, :][0] < in_grids[ind][2] and
                                np_array[coordinate_ind, :][1] >= in_grids[ind][1] and np_array[coordinate_ind, :][1] < in_grids[ind][3]):
                                tmp_array[ind] += 1                
        
                for ind2 in range(len(in_grids)):
                    if tmp_array[ind2] > 0:
                        road_counts_his[ind2] += 1
        # ==========================================
        # write out a csv file
        csv_matrix = []
        csv_matrix.append(['grid_id', 'err_roads', 'road_counts'])
        for index in range(len(in_grids)):
            csv_matrix.append([index + 1, in_counts[index], road_counts_his[index]])
            
        with open(os.path.join(out_folder, 'road-' + os.path.basename(out_folder) + '.csv'), "w") as out_f:
            writer = csv.writer(out_f)
            writer.writerows(csv_matrix)

# =======================================
def get_argument():
    # declare arguments and variables
    parser = argparse.ArgumentParser()
    parser.add_argument('--maxDepth', type = str, default='', help='max depth of a k-d tree')
    parser.add_argument('--countNum', type = str, default='', help='a count value')
    parser.add_argument('--gridPercent', type = str, default='', help='a grid percentage')
    parser.add_argument('--maxCount', type = str, default='', help='maximum count to the second k-d tree')
    parser.add_argument('--outFolder', type = str, default='', help='path to an ouput folder')
    args = parser.parse_args()
    max_count = -1
    
    if args.maxCount:
        max_count = int(args.maxCount)
    
    return args.maxDepth, args.outFolder, int(args.countNum), float(args.gridPercent), max_count

# =======================================
def stop_condition(count_zero_list, count_list, grid_percent, count_num, cell_num, out_distribution):
    # varialbes
    smallest_max_count = 0
    smallest_max_count_ind = -1
    stop_flag = False
    
    # add zeon-count back to the count list and find a maximum count that is smaller than a threshold
    if count_zero_list:
        count_list.insert(0, count_zero_list[0])
    for ind, ele in enumerate(count_list):
        if ele > count_num:
            break
        else:
            smallest_max_count = ele
            smallest_max_count_ind = ind
    # check the stop condition
    if smallest_max_count_ind != -1:
        total_count_within_count_num = 0
        total_grids = 0
        list_length = 0

        if not count_zero_list:  # the list is empty
            list_length = smallest_max_count_ind + 1
            total_grids = cell_num
        else:
            list_length = smallest_max_count_ind + 2
            total_grids = cell_num + count_zero_list[1]

        for i in range(list_length):
            if count_list[i] == 0:
                total_count_within_count_num += count_zero_list[1]
            else:
                total_count_within_count_num += out_distribution[count_list[i]]
        
        if (float(total_count_within_count_num) / float(total_grids)) > grid_percent:
            stop_flag = True
            
    return stop_flag

# =======================================
def extend_partition(depth_count, input_bounding_box, input_data, startId):
    # build k-d tree
    tree_cons = kdTree(depth_count, input_bounding_box, input_data, startId)
    kd_tree= tree_cons.tree_building()

    # get all the leaves given a K-D tree
    bounding_box_collection = tree_cons.get_leaves(kd_tree)

    # get counts
    count_list, gridid_collec= tree_cons.counts_calculation()

    return bounding_box_collection, count_list, gridid_collec
# =======================================
def main():
    # get all arguments and initialize variables
    maximum_level, folder_path, count_num, grid_percent, max_count = get_argument()
    flag_val = False
    input_data = None
    
    path = 'histogram'
    geojson_path = 'geojson'
    
    if not os.path.exists(os.path.join(folder_path, path)):
        sys.stderr.write('Create the histogram directory !! \n')
        os.makedirs(os.path.join(folder_path, path))
    if not os.path.exists(os.path.join(folder_path, geojson_path)):
        sys.stderr.write('Create the geojson directory !! \n')
        os.makedirs(os.path.join(folder_path, geojson_path))
    
    # read the entire data from standard input
    for line in sys.stdin.readlines():
        input_data = ast.literal_eval(line)
    
    # save the 2d list as a file
    with open(os.path.join(folder_path, os.path.basename(input_data['inFolder']) + '.csv' )  , "w") as out_f:
        writer = csv.writer(out_f)
        writer.writerows(input_data['nameNum'])
    
    # perform the 1st k-d tree
    for depth_count in range(1, int(maximum_level) + 1):
        bb_collec, hist, _ = extend_partition(depth_count, input_data['iniBb'], input_data['data'], 1)

        util = Utility(hist)
        filename = os.path.join(os.path.join(folder_path, path), 'level-' + str(depth_count) + '.png')
        # probability distribution
        out_distribution, count_list, count_zero_list, cell_num = util.distribution_computation(filename)
        # write out a Geojson file
        util.geojson_write(depth_count, bb_collec, os.path.join(folder_path, geojson_path), cell_num, input_data['iniArea'], None, 'tree_v1', flag_val)
        del util
        
        # stop condition (the over 90% (parameter) of cells is less than 10 (parameter) (the count value))
        if stop_condition(count_zero_list, count_list, grid_percent, count_num, cell_num, out_distribution):
            # calculate areas
            grid_area = input_data['iniArea'] / (2**(depth_count))
            grid_area = round(grid_area * 1e-6, 2)

            util = Utility(hist)
            # wirte out one row
            util.summary_table_row_generation(input_data['data'], input_data['nameNum'], round(input_data['iniArea'] * 1e-6, 2), grid_area)

            # write out a Geojson file
            util.geojson_write(depth_count, bb_collec, os.path.join(folder_path, geojson_path), cell_num, input_data['iniArea'],
                               None, 'tree_v1', flag_val = True)
            del util

            # ====================================
            # perform the 2nd k-d tree
            if max_count != -1:                
                new_grids_list = []
                new_counts_list = []
                new_area_list = []
                new_grid_id_list = []
                grid_ids = []
                gridid_start = 1
                
                # find all grid indices in which the count is greater the max count
                big_grid_index_list = [index_value for index_value in range(hist.shape[0]) if hist[index_value] > max_count]
                
                if big_grid_index_list:
                    # refine big grids through applying the 2nd K-D tree
                    for extension_ind in big_grid_index_list:
                        for depth_num in range(1, int(maximum_level) + 1):
                            new_bb_collec, new_counts_collec, new_grid_id_collec = extend_partition(depth_num, bb_collec[extension_ind], input_data['data'], gridid_start)
                            new_grid_id_list.append(new_grid_id_collec)

                            # calculate areas
                            new_area = grid_area / (2** depth_num)
                            new_area_list.append(new_area)

                            # update the start point of the grid id
                            gridid_start += len(new_bb_collec)

                            # stop condition
                            if len([x for x in new_counts_collec if x < max_count]) == len(new_counts_collec):
                                for small_ind in range(len(new_bb_collec)):
                                    grid_ids.append(gridid_start + small_ind - len(new_bb_collec))
                                    new_grids_list.append(new_bb_collec[small_ind])
                                    new_counts_list.append(new_counts_collec[small_ind])
                                break
                    # ==============================
                    util = Utility(new_counts_list)
                    # write out a Geojson file
                    util.geojson_write(depth_count, new_grids_list,
                                       os.path.join(folder_path, geojson_path), None, None, grid_ids, 'cascade-kdtree', flag_val = True)
                    del util
            # ====================================
            # road counts
            if input_data['roadFile']:
                road_count(input_data['roadFile'], bb_collec, hist, folder_path, input_data['iniBb'])
            break
    # ======================================
if __name__ == "__main__":
    main()
