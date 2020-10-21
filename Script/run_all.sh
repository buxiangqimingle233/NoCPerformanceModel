#!/bin/bash
task_graph_path="Temp/taskGraph.txt"
comm_graph_path="Temp/CommGraph.txt"
config_path="Configuration/baseline.json"
directive_path="Data/test.txt"
pe_diameter=4
cd ..
# python Mapping/graphGen.py -d $pe_diameter -o $comm_graph_path
python Analyzer/analyzer.py -i $directive_path -o $task_graph_path -c $config_path
python Mapping/SA.py -i $task_graph_path -o $comm_graph_path -d $pe_diameter
python Driver/SDriver.py -i $comm_graph_path -c $config_path
