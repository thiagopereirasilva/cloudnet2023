#!/bin/bash

# Use of PythonEnv (optional)
source ./venv/bin/activate

path_program=$PWD
parallelism=false
cpu_usage="50%"
rep=0
PATH_PACKET_FLOW_FILE="NULL"
user_mobility_file="NULL"

function printUsage()
{
  echo "USAGE: run_experiment.sh -e|--experiment <experiment_id> [-p|--parallelism] [-u|--usage] <cpu_usage> [-r|--repetitions] <number_of_repetitions>"
}

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -p|--parallelism)
    parallelism=true
    shift # past argument
    ;;
    -u|--cpuusage)
    cpu_usage="$2"
    shift # past argument
    shift # past value
    ;;
    -e|--experiment)
    experiment="$2"
    shift # past argument
    shift # past value
    ;;
    -r|--repetitions)
    rep="$2"
    shift # past argument
    shift # past value
    ;;
    *)    # unknown option
    POSITIONAL+=("$1") # save it in an array for later
	  echo "Unknown option: $1"
    printUsage
    shift # past argument
	exit
    ;;
esac
done

# Types of Debug
# 0 = None
# 1 = Simulation
# 3 = Placement
export NSS_DEBUG=0

export NSS_ERROR_PATH="${path_program}/Experiment/Results/Placement/Error"

# Define if the images from placement will be generated or not
export NSS_SAVE_IMAGE_PLACEMENT=0

# Define if will be used the restriction in the links
export COMPUTE_LINK_BW_LIMIT=0

if [[ -z "$experiment" ]]; then
  echo "Experiment not specified!"
  printUsage
	exit 1
fi

if [ "$experiment" = "Q0" ]; then
  exp_name="Q0"
  exp_description="Comparing the number SFC Requests accepted between different placement algorithm!"
  ## declare -a algs=("alg_random_vnf_shareable" "alg_greedy_vnf_shareable" "alg_smart")
  ## declare -a algs=("alg_smart" "alg_random" "alg_greedy")
  declare -a arr=("bf")
  declare -a algs=("alg_smart")
  export PATH_PACKET_FLOW_FILE="${path_program}/Experiment/Q0/packets.csv"

elif [ "$experiment" = "Q1" ]; then
  exp_name="Q1"
  exp_description="Does the proposed placement algorithm reduce the amount of CPU usage in the edge environment, compared with other approaches?"
  declare -a algs=("alg_smart" "alg_greedy" "alg_random")
  declare -a arr=("bf")

elif [ "$experiment" = "Q4" ]; then
  exp_name="Q4"
  exp_description="Does the adoption of the SFC Similarity Metric reduce the number of SFC Requests not met in comparison with the approach that does not use SFC Similarity Metric? "
  declare -a algs=("asc" "desc" "none")
  declare -a arr=("bf")

elif [ "$experiment" = "Q5" ]; then
  exp_name="Q5"
  exp_description="Does the adoption of a bigger Time Window reduce the number of SFC Request not met in comparison with the approach with a smaller Time Window? "
  declare -a algs=("t100" "t500" "t1000")
  declare -a arr=("bf")

elif [ "$experiment" = "Q7" ]; then
  exp_name="Q7"
  exp_description="Does the proposed placement algorithm reduce the total packet processing time (Total Delay) in comparison with other approaches? "
  declare -a algs=("alg_smart" "alg_greedy" "alg_random")
  declare -a arr=("bf")

elif [ "$experiment" = "Q9" ]; then
  exp_name="Q9"
  exp_description="Does the proposed placement algorithm increase the number of SFC Requests met in comparison with other approaches? "
  declare -a algs=("alg_smart" "alg_greedy")
  declare -a arr=("bf")

elif [ "$experiment" = "Q10b" ]; then
  exp_name="Q10b"
  exp_description="Does the proposed placement algorithm increase the number of SFC Requests met in comparison with other approaches? "
  declare -a algs=("alg_smart_not_share" "alg_smart_share")
  declare -a arr=("bf_vnf_share_enabled_multiple" "bf_vnf_share_disabled_multiple")
  #declare -a arr=("bf_vnf_share_enabled" "bf_vnf_share_disabled")

elif [ "$experiment" = "Q1_G2" ]; then
  exp_name="Q1_G2"
  exp_description="Does the sharing mechanism reduce the amount of CPU usage in the edge environment?"
  declare -a algs=("alg_smart_not_share" "alg_smart_share")
  declare -a arr=("bf_vnf_share_enabled_multiple" "bf_vnf_share_disabled_multiple")
  #declare -a arr=("bf_vnf_share_enabled" "bf_vnf_share_disabled")

elif [ "$experiment" = "Q9_G2" ]; then
  exp_name="Q9_G2"
  exp_description="Does the sharing mechanism reduce the amount of CPU usage in the edge environment?"
  declare -a algs=("alg_smart_not_share" "alg_smart_share" "alg_greedy" "alg_random")
  declare -a arr=("bf_vnf_share_enabled_multiple" "bf_vnf_share_disabled_multiple")

elif [ "$experiment" = "Q3_G2" ]; then
  exp_name="Q3_G2"
  exp_description="Does the sharing mechanism reduce the amount of link usage in the edge environment?"
  declare -a algs=("alg_smart_not_share" "alg_smart_share")
  declare -a arr=("bf_vnf_share_enabled_multiple" "bf_vnf_share_disabled_multiple")
  export PATH_PACKET_FLOW_FILE="${path_program}/Experiment/Q3_G2/packets.csv"

elif [ "$experiment" = "Q11" ]; then
  exp_name="Q11"
  exp_description="Does the user mobility impact the SLA Violation?"
  declare -a algs=("user_fixed" "user_moving")
  declare -a arr=("bf")

elif [ "$experiment" = "Q0_ScalingQueue" ]; then
  exp_name="Q0_ScalingQueue"
  exp_description="Testing the Smart Scaling UpDown"
# declare -a algs=("alg_smart" "alg_greedy" "alg_random")
  declare -a algs=("alg_smart" "alg_random")
  declare -a arr=("bf")
  export PATH_PACKET_FLOW_FILE="${path_program}/Experiment/Q0_ScalingQueue/packets.csv"

elif [ "$experiment" = "Q0_UpDown" ]; then
  exp_name="Q0_UpDown"
  exp_description="Testing the Smart Scaling UpDown"
  declare -a algs=("Smart" "Rule" "Queue")
  # declare -a algs=("Queue")
  declare -a arr=("bf")
  export PATH_PACKET_FLOW_FILE="${path_program}/Experiment/Q0_UpDown/packets.csv"
fi

# The number of the first experiment executed
k=0

# The number of the last experiment executed
exp_num=$rep

exp_path_result="${path_program}/Experiment/Results/${exp_name}"

user_mobility_file="Mobility/user_mobility.csv"

# Create experiment folder
if [ ! -d $exp_path_result ]; then
  mkdir $exp_path_result
  mkdir $exp_path_result"/Provenance"
  mkdir $exp_path_result"/Images"
fi

function runExperiment()
{
  exp_name=$1
  exp_description=$2
  path_program=$3
  user_mobility_file=$4
  exp_path_result=$5
  z=$6
  envir=$7
  alg=$8

  #echo $exp_name
  #echo $exp_description
  #echo $path_program
  #echo $user_mobility_file
  #echo "Algorithm: $alg"
  #echo "Environment: $envir"
  #echo $z
  #return

  # Create config file folder
  config_path="${path_program}/Experiment/Results/${exp_name}/Provenance"
  if [ ! -d $config_path ]; then
    mkdir $config_path
  fi

  echo $exp_description > $config_path"/description.txt"

  exp="${exp_name}/Env_$z"

  # Generate a sequential seed or use the provided one
  seed=$random_seed
  if [ "${random_seed}" == "" ]; then
    seed=$z
  fi

    specs_file="${path_program}/Experiment/${exp_name}/${envir}.json"

    echo "Start ${alg}.json algorithm for ${envir} environment"

    simulation_file="${path_program}/Experiment/${exp_name}/${alg}.json"

    if [[ ! $user_mobility_file = "NULL" ]]; then
      if [[ -f "$user_mobility_file" ]]; then
        cp "$user_mobility_file" "${exp_path_result}/Provenance/mobility_file_pattern.txt"
      fi
    fi

    if [[ ! $PATH_PACKET_FLOW_FILE = "NULL" ]]; then
      if [[ -f "$PATH_PACKET_FLOW_FILE" ]]; then
        cp $PATH_PACKET_FLOW_FILE "${exp_path_result}/Provenance/packets.csv"
      fi
    fi

    cp "$specs_file" "${exp_path_result}/Provenance/environment_${envir}.json"
    cp "$simulation_file" "${exp_path_result}/Provenance/simulation_${alg}.json"

    path_result_files="$path_program/Experiment/Results/$exp/${envir}/${alg}"

    #python3 -m scalene --html --reduced-profile --outfile=out.html $path_program/main.py \

    #echo "Simulation File: $simulation_file" 
    #echo "Environment File: $specs_file" 
    time python3 $path_program/main.py \
      --simulation_parameters="$simulation_file" \
      --specs="$specs_file" \
      --path_result_files="$path_result_files" \
      --random_seed=$seed
        # --list=1
        # --save=./Entities.json
        # --user_mobility_file=$user_mobility_file

      #read up rest </proc/uptime
      #t2="${up%.*}${up#*.}"
      #millisec=$((10 * (t2 - t1)))
      #echo "Experiment Duration: $millisec ms"
}

echo "Executing Experiment: ${exp_name}"

if [ "$parallelism" = true ]; then
  export -f runExperiment
  time parallel --bar --jobs $cpu_usage --halt now,fail=1 runExperiment $exp_name \"$exp_description\" \"$path_program\" \"$user_mobility_file\" \"$exp_path_result\" ::: $(seq $k ${exp_num}) ::: ${arr[@]} ::: ${algs[@]} 
else
  while (($k <= $exp_num)); do
    for i in "${arr[@]}"; do
      for j in "${algs[@]}"; do
        runExperiment $exp_name "${exp_description}" "$path_program" "$user_mobility_file" "$exp_path_result" $k $i $j
      done
    done
    ((k = $k + 1))
  done
fi

# For testing the system and find bottlenecks in the source code
#python3 -m scalene --html --reduced-profile --outfile=out.html main.py \
#  --simulation_parameters="Experiment/Q11/user_fixed.json" \
#  --specs="Experiment/Q11/bf.json" \
#  --path_result_files="Experiment/Results/Q11" \
#  --random_seed=1 \
#  --user_mobility_file="Mobility/user_mobility.csv"