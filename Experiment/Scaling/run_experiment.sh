#! /bin/bash

# Use of PythonEnv (optional)
source ../../venv/bin/activate

# path_program="/home/battisti/versionado/nss/"
path_program="/home/thiago/Desktop/nss/"

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

exp_name="Scaling"
exp_description="Testing the Scaling Algorithms".
# declare -a algs=("smart-exp")
# declare -a algs=("queue-exp")
# declare -a algs=("smart-exp" "ruled-based" "queue-exp")
declare -a algs=("queue-exp")
declare -a arr=("bf")
export PATH_PACKET_FLOW_FILE="${path_program}/Experiment/Scaling/maracana_workload.csv"
export NSS_LOG_TOTAL_RESOURCES=1

# The number of the first experiment executed
k=0

# The number of the last experiment executed
exp_num=0

exp_path_result="${path_program}/Experiment/Results/${exp_name}"

# Create experiment folder
if [ ! -d $exp_path_result ]; then
  mkdir $exp_path_result
  mkdir $exp_path_result"/Provenance"
  mkdir $exp_path_result"/Images"
fi

while (($k <= $exp_num)); do

  echo "Executing Environment: ${exp_name}"
  echo ""

  # Create config file folder
  config_path="${path_program}/Experiment/Results/${exp_name}/Provenance"
  if [ ! -d $config_path ]; then
    mkdir $config_path
  fi

  echo $exp_description > $config_path"/description.txt"

  exp="${exp_name}/Env_$k"

  # Generate a sequential seed or use the provided one
  seed=$random_seed
  if [ "${random_seed}" == "" ]; then
    seed=$k
  fi

  for i in "${arr[@]}"; do

    specs_file="${path_program}/Experiment/${exp_name}/${i}.json"

    for j in "${algs[@]}"; do
      read up rest </proc/uptime
      t1="${up%.*}${up#*.}"
      echo "Start ${i}.json algorithm for ${j} environment"

      simulation_file="${path_program}/Experiment/${exp_name}/${j}.json"

      if [[ -n $PATH_PACKET_FLOW_FILE ]]; then
        cp $PATH_PACKET_FLOW_FILE "${exp_path_result}/Provenance/packets.csv"
      fi

      cp "$specs_file" "${exp_path_result}/Provenance/environment_${i}.json"
      cp "$simulation_file" "${exp_path_result}/Provenance/simulation_${j}.json"

      path_result_files="$path_program/Experiment/Results/$exp/${i}/${j}"

      python3 -W ignore $path_program/main.py \
        --simulation_parameters="$simulation_file" \
        --specs="$specs_file" \
        --path_result_files="$path_result_files" \
        --random_seed=$seed
        # --list=1
        # --save=./Entities.json

      read up rest </proc/uptime
      t2="${up%.*}${up#*.}"
      millisec=$((10 * (t2 - t1)))
      echo "Experiment Duration: $millisec ms"

    done
  done
  ((k = $k + 1))
done
