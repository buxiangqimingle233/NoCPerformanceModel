#!/bin/bash
comm_graph_path="Temp/CommGraph.txt"
task_graph_path="Data/TaskGraph.txt"
task_graph_name="TaskGraph.txt"
config_name="baseline.json"
d=4
cd ..
python Mapping/graphGen.py -d $d -o $comm_graph_path
python Mapping/SA.py -i $comm_graph_path -o $task_graph_path -d $d
python Driver/SDriver.py -c $config_name --d $task_graph_name
