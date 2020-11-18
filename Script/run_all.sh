#!/bin/bash
task_graph_path="Temp/taskGraph.txt"
comm_graph_path="Temp/commGraph.txt"
directive_path="Data/test.txt"
arch_config_path="Default/dft_arch.json"
usr_config_path="Configuration/baseline.json"
pe_diameter=4
cd ..
# python Mapping/graphGen.py -d $pe_diameter -o $comm_graph_path
# python Analyzer/analyzer.py -o $comm_graph_path -i $directive_path -c $arch_config_path
python Mapping/SA.py -o $task_graph_path -i $comm_graph_path -c $arch_config_path
# python Driver/SDriver.py -i $task_graph_path -uc $usr_config_path -ac $arch_config_path
